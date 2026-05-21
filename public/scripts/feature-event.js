(() => {
  const form = document.querySelector('[data-feature-event-form]');
  const status = document.querySelector('[data-feature-event-status]');
  const imageStatus = document.querySelector('[data-feature-image-status]');
  if (!(form instanceof HTMLFormElement) || !(status instanceof HTMLElement)) return;
  form.noValidate = true;

  const MAX_IMAGE_BYTES = 1.5 * 1024 * 1024;
  let selectedImage = null;

  const setStatus = (message, tone = 'neutral') => {
    status.textContent = message;
    status.dataset.tone = tone;
  };

  const setImageStatus = (message, tone = 'neutral') => {
    if (!(imageStatus instanceof HTMLElement)) return;
    imageStatus.textContent = message;
    imageStatus.dataset.tone = tone;
  };

  const fieldValue = (name) => {
    const field = form.elements.namedItem(name);
    if (field instanceof HTMLInputElement || field instanceof HTMLTextAreaElement) return field.value.trim();
    return '';
  };

  const checkedValue = (name) => {
    const field = form.querySelector(`input[name="${name}"]:checked`);
    return field instanceof HTMLInputElement ? field.value : '';
  };

  const fileToDataUrl = (file) => new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ''));
    reader.onerror = () => reject(new Error('Unable to read that image.'));
    reader.readAsDataURL(file);
  });

  const imageDimensions = (dataUrl) => new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve({ width: image.naturalWidth, height: image.naturalHeight });
    image.onerror = () => reject(new Error('That image could not be opened.'));
    image.src = dataUrl;
  });

  const formatBytes = (bytes) => {
    if (!Number.isFinite(bytes)) return '';
    if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
    return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  };

  const imageUpload = form.elements.namedItem('imageUpload');
  if (imageUpload instanceof HTMLInputElement) {
    imageUpload.addEventListener('change', async () => {
      selectedImage = null;
      const file = imageUpload.files?.[0];
      if (!file) {
        setImageStatus('No image selected yet.');
        return;
      }
      if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
        imageUpload.value = '';
        setImageStatus('Please use a JPG, PNG, or WebP image.', 'error');
        return;
      }
      if (file.size > MAX_IMAGE_BYTES) {
        imageUpload.value = '';
        setImageStatus('That image is too large. Please keep uploads under 1.5 MB.', 'error');
        return;
      }
      try {
        setImageStatus('Checking image…');
        const dataUrl = await fileToDataUrl(file);
        const dimensions = await imageDimensions(dataUrl);
        selectedImage = {
          name: file.name,
          mime: file.type,
          size: file.size,
          width: dimensions.width,
          height: dimensions.height,
          dataUrl
        };
        setImageStatus(`Selected: ${file.name} · ${dimensions.width} × ${dimensions.height}px · ${formatBytes(file.size)}`, 'success');
        const providedChoice = form.querySelector('input[name="imagePreference"][value="provided"]');
        if (providedChoice instanceof HTMLInputElement) providedChoice.checked = true;
      } catch (error) {
        selectedImage = null;
        imageUpload.value = '';
        setImageStatus(error instanceof Error ? error.message : 'Unable to read that image.', 'error');
      }
    });
  }

  const imageUrlField = form.elements.namedItem('imageUrl');
  if (imageUrlField instanceof HTMLInputElement) {
    imageUrlField.addEventListener('input', () => {
      if (imageUrlField.value.trim()) {
        const providedChoice = form.querySelector('input[name="imagePreference"][value="provided"]');
        if (providedChoice instanceof HTMLInputElement) providedChoice.checked = true;
      }
    });
  }

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const button = form.querySelector('button[type="submit"]');
    const originalButtonText = button instanceof HTMLButtonElement ? button.textContent : '';
    if (button instanceof HTMLButtonElement) {
      button.disabled = true;
      button.textContent = 'Submitting…';
    }
    const missing = [];
    if (!fieldValue('eventDate')) missing.push('date');
    if (!fieldValue('venue')) missing.push('venue');
    if (!fieldValue('city')) missing.push('city/area');
    if (!fieldValue('description')) missing.push('description');
    if (!fieldValue('organizerName')) missing.push('organizer name');
    if (!fieldValue('organizerEmail')) missing.push('email/contact');
    setStatus(missing.length ? `Saving your event details. Missing: ${missing.join(', ')} — you can still submit.` : 'Saving your event details…');

    const payload = {
      website: fieldValue('website'),
      eventName: fieldValue('eventName'),
      eventDate: fieldValue('eventDate'),
      eventTime: fieldValue('eventTime'),
      venue: fieldValue('venue'),
      city: fieldValue('city'),
      address: fieldValue('address'),
      eventUrl: fieldValue('eventUrl'),
      ticketUrl: fieldValue('ticketUrl'),
      description: fieldValue('description'),
      imagePreference: checkedValue('imagePreference') || 'generate',
      imageUrl: fieldValue('imageUrl'),
      imageNotes: fieldValue('imageNotes'),
      imageUploadName: selectedImage?.name || '',
      imageUploadMime: selectedImage?.mime || '',
      imageUploadSize: selectedImage?.size || 0,
      imageUploadWidth: selectedImage?.width || 0,
      imageUploadHeight: selectedImage?.height || 0,
      imageUploadDataUrl: selectedImage?.dataUrl || '',
      organizerName: fieldValue('organizerName'),
      organizerEmail: fieldValue('organizerEmail'),
      organizerPhone: fieldValue('organizerPhone'),
      expectedAttendance: fieldValue('expectedAttendance'),
      notes: fieldValue('notes')
    };

    try {
      const response = await fetch('/api/event-submissions', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok || !data.ok) throw new Error(data.error || 'Something went sideways. Please try again.');

      if (data.paymentUrl) {
        setStatus('Saved. Sending you to secure payment…', 'success');
        if (button instanceof HTMLButtonElement) button.textContent = 'Opening payment…';
        window.location.assign(data.paymentUrl);
        return;
      }

      form.reset();
      selectedImage = null;
      setImageStatus('No image selected yet.');
      setStatus(data.message || 'Submission saved. LeeScoop will follow up with payment instructions.', 'success');
      status.scrollIntoView({ behavior: 'smooth', block: 'center' });
      if (button instanceof HTMLButtonElement) {
        button.disabled = false;
        button.textContent = originalButtonText || 'Submit event and continue to payment';
      }
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Something went sideways. Please try again.', 'error');
      status.scrollIntoView({ behavior: 'smooth', block: 'center' });
      if (button instanceof HTMLButtonElement) {
        button.disabled = false;
        button.textContent = originalButtonText || 'Submit event and continue to payment';
      }
    }
  });
})();
