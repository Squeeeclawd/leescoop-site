import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, MagicMock
import publishing_source_fetch as f


class FetchTests(unittest.TestCase):
    def config(self):
        return {'nearbyEnabled':False,'sources':[{'id':'fixture','url':'https://example.com','lane':'lee'}],
                'network':{'maxPagesPerRun':24,'maxPagesPerHost':3,'minSecondsPerHost':5,'timeoutSeconds':20,'maxResponseBytes':2000000}}

    def test_url_and_dns_fail_closed(self):
        for url in ('http://example.com/x','https://a:b@example.com/x','https://example.com:444/x','https://example.com/x#fragment','https://other.com/x','https://127.0.0.1/x'):
            with self.assertRaises(ValueError):f.public_url(url,{'example.com'})
        with patch.object(f.socket,'getaddrinfo',return_value=[(2,1,6,'',('93.184.216.34',443)),(2,1,6,'',('127.0.0.1',443))]):
            with self.assertRaises(ValueError):f.public_addresses('example.com')

    def test_delay_and_backward_clock(self):
        self.assertEqual(f.remaining_delay(100,102,5),3)
        self.assertEqual(f.remaining_delay(100,106,5),0)
        with self.assertRaises(ValueError):f.remaining_delay(100,99,5)

    def test_budgets_block_before_network(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(f,'public_addresses') as dns:
            state=Path(tmp);journal={'requests':[{'host':'example.com','status':200}]*3}
            with self.assertRaisesRegex(ValueError,'host request cap'):
                f.request('https://example.com/x',state=state,run='run',config=self.config(),journal=journal)
            dns.assert_not_called()
            journal={'requests':[{'host':'other.com','status':200}]*24}
            with self.assertRaisesRegex(ValueError,'run request cap'):
                f.request('https://example.com/x',state=state,run='run',config=self.config(),journal=journal)

    def test_actual_request_waits_and_defers_429(self):
        with tempfile.TemporaryDirectory() as tmp:
            state=Path(tmp);f.save(state/'source-access/hosts.json',{'example.com':{'startedEpoch':100}})
            connection=MagicMock();response=connection.getresponse.return_value
            response.status=429;response.getheaders.return_value=[('Content-Type','text/plain'),('Retry-After','120')];response.read.return_value=b'limited'
            with patch.object(f.time,'time',return_value=102),patch.object(f.time,'sleep') as sleep,patch.object(f,'public_addresses',return_value=['93.184.216.34']),patch.object(f,'PinnedHTTPS',return_value=connection):
                status,headers,body,record=f.request('https://example.com/x',state=state,run='run',config=self.config(),journal={'requests':[]})
                sleep.assert_called_once_with(3)
                self.assertEqual(status,429)
                with self.assertRaisesRegex(ValueError,'deferred'):
                    f.request('https://example.com/y',state=state,run='run',config=self.config(),journal={'requests':[]})
                self.assertEqual(connection.request.call_count,1)

    def test_robots_disallow_and_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            state=Path(tmp)
            with patch.object(f,'request',return_value=(200,{},b'User-agent: *\nDisallow: /private\n',{})):
                with self.assertRaisesRegex(ValueError,'robots disallows'):
                    f.check_robots('https://example.com/private',state,'run',self.config(),{})
                result=f.check_robots('https://example.com/public',state,'run',self.config(),{})
                self.assertEqual(result['status'],200)
        with tempfile.TemporaryDirectory() as tmp,patch.object(f,'request',return_value=(404,{},b'',{})):
            self.assertEqual(f.check_robots('https://example.com/public',Path(tmp),'run',self.config(),{})['status'],404)

    def test_redirect_revalidates_and_text_has_no_script(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(f,'check_robots',return_value={}),patch.object(f,'request',return_value=(302,{'location':'https://127.0.0.1/private'},b'',{})):
            with self.assertRaises(ValueError):f.fetch('https://example.com/x',Path(tmp),'run',self.config())
        reader=f.TextReader();reader.feed('<h1>Actual event</h1><script>malicious()</script><a href="/detail">Detail</a>')
        self.assertNotIn('malicious',''.join(reader.parts));self.assertEqual(reader.links,['/detail'])

    def test_oversized_response_is_not_saved_as_verified_document(self):
        with tempfile.TemporaryDirectory() as tmp:
            config=self.config();config['network']['maxResponseBytes']=4
            connection=MagicMock();r=connection.getresponse.return_value;r.status=200;r.getheaders.return_value=[];r.read.return_value=b'large'
            with patch.object(f,'public_addresses',return_value=['93.184.216.34']),patch.object(f,'PinnedHTTPS',return_value=connection):
                with self.assertRaisesRegex(ValueError,'byte budget'):
                    f.request('https://example.com/x',state=Path(tmp),run='run',config=config,journal={})


if __name__=='__main__':unittest.main()
