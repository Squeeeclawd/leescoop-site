import copy
from datetime import datetime, timedelta
import json
from pathlib import Path
from types import SimpleNamespace
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import publishing_workflow as w


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((w.ROOT / "docs/workflow/sources.json").read_text())
        self.now = datetime.fromisoformat("2026-09-18T14:00:00-04:00")
        for tier, model in (("routine", "openai/gpt-5.6-luna"), ("review", "openai/gpt-5.5")):
            self.config["routes"][tier].update(
                model=model, auth="oauth", evidence="fixture config attestation",
                verifiedAt=self.now.isoformat(), expiresAt=(self.now + timedelta(hours=2)).isoformat(),
                successfulInferenceReceipt=f"fixture-{tier}-inference",
            )
        self.item = dict(
            kind="event", slug="fixture-only", title="Fixture only",
            sourceId="cape", sourceUrl="https://www.capecoral.gov/fixture", sourceName="Fixture",
            city="Cape Coral", category="Arts", excerpt="Fixture", summary="Fixture",
            date=self.now.isoformat(), evidence="Test only", verified=True, reviewed=True,
            verifiedAt=self.now.isoformat(), score=11, eventDate="2026-09-19T10:00:00-04:00",
            eventTime="10:00 AM - 12:00 PM", venue="Fixture Hall", organizer="Fixture",
            eventType="arts", cost="free", status="scheduled",
            eventVerification={
                "eventPageUrl": "https://www.capecoral.gov/fixture", "observedTitle": "Fixture only",
                "observedDateText": "September 19, 2026 at 10:00 AM", "observedStart": "2026-09-19T10:00:00-04:00",
                "accessedAt": self.now.isoformat(), "receipt": "browser-source-read-fixture",
            },
        )
        self.payload = {
            "workflowEvidence": {
                "routine": {"model": "openai/gpt-5.6-luna", "completedAt": self.now.isoformat(), "receipt": "routine-job-ok"},
                "review": {"model": "openai/gpt-5.5", "completedAt": self.now.isoformat(), "receipt": "review-job-ok"},
            },
            "items": [self.item],
        }

    def write_config(self, directory):
        path = Path(directory) / "config.json"
        path.write_text(json.dumps(self.config))
        return path

    def test_plan_rotation_timezone_and_honest_fetch_mode(self):
        first = w.plan(self.config, self.now.date())
        self.assertEqual(first, w.plan(self.config, self.now.date()))
        self.assertNotEqual(first["sources"], w.plan(self.config, (self.now + timedelta(days=1)).date())["sources"])
        self.assertFalse(any(source["lane"] == "nearby" for source in first["sources"]))
        self.assertFalse(first["automaticFetchAdapter"])

    def test_date_only_and_today_event_semantics(self):
        w.validate(self.item, self.config, self.now)
        today_evidence = dict(self.item["eventVerification"], observedDateText="September 18, 2026", observedStart="2026-09-18")
        w.validate(dict(self.item, eventDate="2026-09-18", eventVerification=today_evidence), self.config, self.now)
        w.validate(dict(self.item, eventDate="2026-09-18T09:00:00-04:00", eventTime="9:00 AM", eventVerification=today_evidence), self.config, self.now)
        past_evidence = dict(today_evidence, observedDateText="September 17, 2026", observedStart="2026-09-17")
        with self.assertRaises(ValueError):
            w.validate(dict(self.item, eventDate="2026-09-17", eventVerification=past_evidence), self.config, self.now)
        multi_evidence = dict(past_evidence, observedEnd="2026-09-20")
        w.validate(dict(self.item, eventDate="2026-09-17", eventEndDate="2026-09-20", eventVerification=multi_evidence), self.config, self.now)
        self.assertEqual(w.event_cutoff(dict(self.item, eventDate="2026-09-18")).hour, 23)
        self.assertEqual(w.event_cutoff(self.item), datetime.fromisoformat("2026-09-19T12:00:00-04:00"))

    def test_private_and_credential_urls_rejected_without_network(self):
        bad = [
            "https://localhost/item", "https://127.0.0.1/item", "https://10.0.0.2/item",
            "https://[::1]/item", "https://user:pass@example.com/item", "http://www.capecoral.gov/item",
        ]
        for url in bad:
            with self.subTest(url=url), self.assertRaises(ValueError):
                w.public_https_url(url)

    def test_event_requires_actual_title_date_extraction(self):
        missing = dict(self.item); missing.pop("eventVerification")
        with self.assertRaisesRegex(ValueError, "title/date extraction"):
            w.validate(missing, self.config, self.now)
        mismatch = copy.deepcopy(self.item); mismatch["eventVerification"]["observedStart"] = "2026-09-20T10:00:00-04:00"
        with self.assertRaisesRegex(ValueError, "does not match"):
            w.validate(mismatch, self.config, self.now)
        title_only = copy.deepcopy(self.item); title_only["eventVerification"]["observedDateText"] = "Calendar"
        # A nonempty label alone is insufficient if its structured observed date disagrees.
        title_only["eventVerification"]["observedStart"] = "2025-09-19T10:00:00-04:00"
        with self.assertRaises(ValueError):
            w.validate(title_only, self.config, self.now)

    def test_bounded_source_registry(self):
        with self.assertRaises(ValueError):
            w.validate(dict(self.item, sourceUrl="https://example.org/fixture"), self.config, self.now)
        with self.assertRaises(ValueError):
            w.validate(dict(self.item, sourceId="missing"), self.config, self.now)

    def test_nearby_explicit(self):
        evidence = dict(self.item["eventVerification"], eventPageUrl="https://www.naplesgov.com/event")
        item = dict(self.item, city="Naples", sourceId="naples", sourceUrl="https://www.naplesgov.com/event", eventVerification=evidence, coverageLabel="Nearby Southwest Florida", exceptionReason="Exceptional fixture")
        with self.assertRaises(ValueError):
            w.validate(item, self.config, self.now)
        self.config["nearbyEnabled"] = True
        w.validate(item, self.config, self.now)

    def test_dedupe(self):
        evidence = dict(self.item["eventVerification"], observedTitle="Different fixture")
        other = dict(self.item, slug="different", title="Different", sourceUrl="https://www.capecoral.gov/fixture?utm_source=test", eventVerification=evidence)
        with patch.object(w, "cover", return_value="hash"):
            accepted, rejected, _ = w.evaluate([self.item, other], self.config, self.now, w.ROOT, {})
        self.assertEqual(len(accepted), 1)
        self.assertIn("duplicate", rejected[0]["reason"])

    def test_event_cover_policy_blocks_source_bypass(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); covers = root / "public/covers"; covers.mkdir(parents=True)
            path = covers / "fixture.png"; Image.new("RGB", (1216, 704)).save(path)
            source = dict(self.item, coverImage="/covers/fixture.png", coverOrigin="source", sourceImageUrl="https://www.capecoral.gov/image.png")
            with self.assertRaises(ValueError):
                w.cover(source, root, self.config, self.now)
            existing = dict(self.item, coverImage="/covers/fixture.png", coverOrigin="existing", coverReviewed=True, coverPreservationEvidence="reviewed existing asset")
            with patch.object(w, "tracked_pristine", return_value=True):
                self.assertEqual(len(w.cover(existing, root, self.config, self.now)), 64)

    def test_news_source_image_requires_attribution_rights_and_host(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); covers = root / "public/covers"; covers.mkdir(parents=True)
            Image.new("RGB", (100, 100)).save(covers / "fixture.jpg")
            item = dict(self.item, kind="news", coverImage="/covers/fixture.jpg", coverOrigin="source", sourceImageUrl="https://www.capecoral.gov/image.jpg")
            for field in ("sourceImageAttribution", "sourceImageRightsEvidence"):
                candidate = dict(item, sourceImageAttribution="City", sourceImageRightsEvidence="source page permits editorial use")
                candidate.pop(field)
                with self.subTest(field=field), self.assertRaises(ValueError):
                    w.cover(candidate, root, self.config, self.now)
            item.update(sourceImageAttribution="City", sourceImageRightsEvidence="source page permits editorial use")
            self.assertEqual(len(w.cover(item, root, self.config, self.now)), 64)
            with self.assertRaises(ValueError):
                w.cover(dict(item, sourceImageUrl="https://cdn.example.net/image.jpg"), root, self.config, self.now)

    def test_routes_and_job_receipts_fail_closed(self):
        for tier in ("routine", "review"):
            self.assertEqual(w.route(self.config, tier, self.now), self.config["routes"][tier]["model"])
        broken = copy.deepcopy(self.config)
        broken["routes"]["routine"].pop("successfulInferenceReceipt")
        with self.assertRaises(ValueError):
            w.route(broken, "routine", self.now)
        with self.assertRaises(ValueError):
            w.route(self.config, "image", self.now)
        with self.assertRaises(ValueError):
            w.route_evidence({"workflowEvidence": {}}, self.config, "routine", self.now)
        stale = copy.deepcopy(self.payload)
        stale["workflowEvidence"]["review"]["completedAt"] = (self.now - timedelta(days=2)).isoformat()
        with self.assertRaises(ValueError):
            w.route_evidence(stale, self.config, "review", self.now)

    def test_lock_concurrent_process(self):
        with tempfile.TemporaryDirectory() as directory:
            with w.lock(Path(directory)):
                code = "from pathlib import Path; from publishing_workflow import lock;\nwith lock(Path(" + repr(directory) + ")): pass"
                result = subprocess.run([sys.executable, "-c", code], cwd=Path(__file__).parent, capture_output=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(b"state lock", result.stderr)

    def test_prepare_gate_input_mutation_and_release_lease(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(w, "cover", return_value="fixturehash"):
            base = Path(directory); source = base / "input.json"; source.write_text(json.dumps(self.payload))
            config = self.write_config(base)
            args = ["--config", str(config), "--state", directory, "--now", self.now.isoformat(), "prepare", "--run", "fixture", "--input", str(source)]
            self.assertEqual(w.main(args), 0)
            gate = ["gate" if value == "prepare" else value for value in args]
            self.assertEqual(w.main(gate), 0)
            changed = copy.deepcopy(self.payload); changed["items"][0]["summary"] = "mutated"
            source.write_text(json.dumps(changed))
            self.assertEqual(w.main(gate), 2)
            other = [value if value != "fixture" else "other" for value in args]
            self.assertEqual(w.main(other), 2)

    def test_materialization_dry_run_atomic_no_overwrite_and_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory); state = base / "state"; root = base / "release"
            (root / "src/content/articles").mkdir(parents=True)
            cover = root / "public/covers/fixture.png"; cover.parent.mkdir(parents=True); cover.write_bytes(b"fixture-cover")
            input_hash = w.digest({})
            checkpoint = w.checkpoint_value(input_hash, [dict(self.item, eventDate="2026-09-19", coverImage="/covers/fixture.png")], {"fixture-only": w.file_hash(cover)}, {"routine": {}, "review": {}})
            w.save(state / "checkpoints/run.json", checkpoint)
            w.save(state / "active-release.json", {"run": "run", "inputHash": input_hash, "releaseHead": "head", "checkpointHash": w.digest(checkpoint), "status": "gated"})
            source = base / "input.json"; source.write_text("{}")
            args = SimpleNamespace(state=state, run="run", input=source, release_root=root, dry_run=True)
            with patch.object(w, "bound_checkpoint", return_value=checkpoint), patch.object(w, "release_head", return_value="head"), patch.object(w, "status_paths", return_value=set()):
                result = w.materialize(args)
                self.assertEqual(result["status"], "dry_run")
                self.assertFalse((root / "src/content/articles/fixture-only.md").exists())
                args.dry_run = False
                w.materialize(args)
                target = root / "src/content/articles/fixture-only.md"
                expected = target.read_text()
                self.assertIn("[Fixture](https://www.capecoral.gov/fixture)", expected)
                self.assertIn("eventDate: 2026-09-19T12:00:00-04:00", expected)
                # Interrupted rerun adopts an exact journal-owned file.
                w.materialize(args)
                target.write_text(expected + "tamper")
                with self.assertRaises(ValueError):
                    w.materialize(args)
                target.write_text(expected)
                cover.write_bytes(b"changed-cover")
                with self.assertRaisesRegex(ValueError, "cover changed"):
                    w.materialize(args)

    def test_finalize_requires_live_receipt_not_push(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory); item = dict(self.item, coverImage="/covers/fixture.png")
            checkpoint = w.checkpoint_value("input", [item], {"fixture-only": "a" * 64}, {"routine": {}, "review": {}})
            w.save(state / "checkpoints/run.json", checkpoint)
            w.save(state / "active-release.json", {"run": "run", "inputHash": "input", "releaseHead": "base", "status": "pushed", "commit": "c" * 40})
            w.save(state / "ledger.json", {"candidate": {"run": "run", "state": "selected", "published": False, "keys": w.keys(item)}})
            receipt_path = state / "receipt.json"
            incomplete = {"run": "run", "commit": "c" * 40}
            receipt_path.write_text(json.dumps(incomplete))
            args = SimpleNamespace(state=state, run="run", receipt=receipt_path)
            with self.assertRaises(ValueError):
                w.finalize(args, self.config)
            checked_at = datetime.now(w.NY).isoformat()
            receipt = {
                "run": "run", "commit": "c" * 40, "productionCommit": "c" * 40,
                "canonicalOrigin": "https://leescoop.com", "checkedAt": checked_at,
                "deploymentReceipt": "cloudflare-pages:deployment:319c8d3a-22db-4dd8-ad40-a4976b701594;github-check-run:105741020376",
                "deploymentProof": {
                    "provider": "cloudflare-pages", "deploymentId": "319c8d3a-22db-4dd8-ad40-a4976b701594",
                    "githubCheckRunId": 105741020376, "headSha": "c" * 40, "conclusion": "success",
                    "completedAt": checked_at,
                    "detailsUrl": "https://github.com/Squeeeclawd/leescoop-site/runs/105741020376",
                    "previewUrl": "https://319c8d3a.leescoop-site.pages.dev",
                },
                "verifiedBy": "parent-liveverify",
                "articles": [{
                    "slug": "fixture-only", "url": "https://leescoop.com/fixture-only/",
                    "coverUrl": "https://leescoop.com/covers/fixture.png", "httpStatus": 200,
                    "title": self.item["title"], "sourceUrl": self.item["sourceUrl"],
                    "coverSha256": "a" * 64, "titleVerified": True, "sourceLinkVerified": True,
                    "coverHashVerified": True, "coverDecoded": True,
                }],
            }
            receipt_path.write_text(json.dumps(receipt))
            result = w.finalize(args, self.config)
            self.assertEqual(result["status"], "published")
            ledger = w.load_json(state / "ledger.json")
            self.assertTrue(ledger["candidate"]["published"])
            self.assertFalse((state / "active-release.json").exists())
            self.assertTrue(w.finalize(args, self.config)["idempotent"])

    def test_finalize_rejects_cf_ray_as_deployment_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory); item = dict(self.item, coverImage="/covers/fixture.png")
            checkpoint = w.checkpoint_value("input", [item], {"fixture-only": "a" * 64}, {"routine": {}, "review": {}})
            w.save(state / "checkpoints/run.json", checkpoint)
            w.save(state / "active-release.json", {"run": "run", "inputHash": "input", "releaseHead": "base", "status": "pushed", "commit": "c" * 40})
            receipt_path = state / "receipt.json"
            receipt_path.write_text(json.dumps({
                "run": "run", "commit": "c" * 40, "productionCommit": "c" * 40,
                "canonicalOrigin": "https://leescoop.com", "checkedAt": datetime.now(w.NY).isoformat(),
                "deploymentReceipt": "cloudflare:cf-ray:not-a-deployment", "verifiedBy": "parent-liveverify",
                "articles": [],
            }))
            with self.assertRaisesRegex(ValueError, "live-verification evidence"):
                w.finalize(SimpleNamespace(state=state, run="run", receipt=receipt_path), self.config)

    def test_status_reconciles_stale_blocked_attempt_from_final_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            receipt = {"run": "run", "commit": "c" * 40}
            receipt_hash = w.digest(receipt)
            w.save(state / "runs/run.json", {"run": "run", "status": "blocked", "error": "stale dirt"})
            w.save(state / "receipts/run.json", receipt)
            w.save(state / "ledger.json", {"candidate": {
                "run": "run", "state": "published", "published": True,
                "commit": "c" * 40, "receiptHash": receipt_hash,
            }})
            result = w.workflow_status(state)
            self.assertEqual(result["runs"][0]["status"], "published")
            self.assertEqual(result["runs"][0]["reconciledFromStatus"], "blocked")
            self.assertNotIn("error", result["runs"][0])
            self.assertEqual(result["runs"][0]["priorError"], "stale dirt")

    def test_legacy_writer_requires_gate_contract(self):
        result = subprocess.run([sys.executable, str(w.ROOT / "scripts/leescoop_posts.py"), "write", "--input", "missing.json"], capture_output=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn(b"--state", result.stderr)

    def test_real_git_lifecycle_mutation_and_crash_recovery(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory); root = base / "repo"; root.mkdir()
            state = base / "state"; remote = base / "remote.git"
            def git(*args):
                return w.git(root, *args)
            git("init", "-b", "main")
            git("config", "user.name", "Fixture")
            git("config", "user.email", "fixture@example.invalid")
            (root / "public/covers").mkdir(parents=True)
            Image.new("RGB", (1216, 704)).save(root / "public/covers/fixture.png")
            git("add", "."); git("commit", "-m", "fixture base")
            subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
            git("remote", "add", "origin", str(remote)); git("push", "origin", "main")
            self.item.update(coverImage="/covers/fixture.png", coverOrigin="existing", coverReviewed=True, coverPreservationEvidence="fixture only")
            source = base / "input.json"; w.save(source, self.payload)
            args = SimpleNamespace(state=state, run="run", input=source, release_root=root, dry_run=False, message="fixture release", remote="origin", branch="main")
            with patch.object(w, "ROOT", root):
                w.prepare_or_gate(args, self.config, self.now, "prepare")
                w.prepare_or_gate(args, self.config, self.now, "gate")
            checkpoint_path = state / "checkpoints/run.json"
            original = w.load_json(checkpoint_path)
            changed = copy.deepcopy(original); changed["selected"][0]["title"] = "tamper"
            w.save(checkpoint_path, changed)
            with self.assertRaisesRegex(ValueError, "checkpoint changed"):
                w.materialize(args)
            w.save(checkpoint_path, original)
            target = root / "src/content/articles/fixture-only.md"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(w.render_articles(original)["src/content/articles/fixture-only.md"]["content"])
            with self.assertRaisesRegex(ValueError, "without journal"):
                w.materialize(args)
            target.unlink()
            w.materialize(args); w.materialize(args)
            # Mock only the expensive quality command list; Git and file integrity stay real.
            with patch.object(w, "QUALITY_COMMANDS", ((sys.executable, "-c", "print('fixture quality')"),)):
                w.quality(args)
            text = target.read_text(); target.write_text(text + "tamper")
            with self.assertRaisesRegex(ValueError, "article changed"):
                w.commit_release(args)
            target.write_text(text)
            cover = root / "public/covers/fixture.png"; image = cover.read_bytes(); cover.write_bytes(image + b"tamper")
            with self.assertRaisesRegex(ValueError, "cover changed"):
                w.commit_release(args)
            cover.write_bytes(image)
            real_save = w.save
            def interrupted_save(path, value):
                if path == state / "active-release.json" and value.get("status") == "committed":
                    raise OSError("fixture crash after git commit")
                real_save(path, value)
            with patch.object(w, "save", side_effect=interrupted_save), self.assertRaises(OSError):
                w.commit_release(args)
            committed = w.commit_release(args)
            self.assertTrue(committed["recovered"])
            self.assertEqual(git("show", "--format=", "--name-only", "HEAD"), "src/content/articles/fixture-only.md")
            def interrupted_push_save(path, value):
                if path == state / "active-release.json" and value.get("status") == "pushed":
                    raise OSError("fixture crash after git push")
                real_save(path, value)
            with patch.object(w, "save", side_effect=interrupted_push_save), self.assertRaises(OSError):
                w.push_release(args, self.config)
            self.assertTrue(w.push_release(args, self.config)["recovered"])
            self.assertFalse(next(iter(w.load_json(state / "ledger.json").values()))["published"])
            commit = committed["commit"]
            checked_at = datetime.now(w.NY).isoformat()
            receipt = dict(
                run="run", commit=commit, productionCommit=commit,
                canonicalOrigin="https://leescoop.com", checkedAt=checked_at,
                deploymentReceipt="cloudflare-pages:deployment:319c8d3a-22db-4dd8-ad40-a4976b701594;github-check-run:105741020376",
                deploymentProof=dict(
                    provider="cloudflare-pages", deploymentId="319c8d3a-22db-4dd8-ad40-a4976b701594",
                    githubCheckRunId=105741020376, headSha=commit, conclusion="success", completedAt=checked_at,
                    detailsUrl="https://github.com/Squeeeclawd/leescoop-site/runs/105741020376",
                    previewUrl="https://319c8d3a.leescoop-site.pages.dev",
                ),
                verifiedBy="parent-liveverify",
                articles=[dict(slug=self.item["slug"], url="https://leescoop.com/fixture-only/", coverUrl="https://leescoop.com/covers/fixture.png", httpStatus=200, title=self.item["title"], sourceUrl=self.item["sourceUrl"], coverSha256=w.file_hash(cover), titleVerified=True, sourceLinkVerified=True, coverHashVerified=True, coverDecoded=True)],
            )
            args.receipt = base / "receipt.json"; w.save(args.receipt, receipt)
            self.assertEqual(w.finalize(args, self.config)["status"], "published")
            self.assertTrue(w.finalize(args, self.config)["idempotent"])
            self.assertFalse(w.active_path(state).exists())
            self.assertEqual(git("status", "--porcelain"), "")

    def test_empty_pool_noop(self):
        self.assertEqual(w.evaluate([], self.config, self.now, w.ROOT, {}), ([], [], {}))


if __name__ == "__main__":
    unittest.main()
