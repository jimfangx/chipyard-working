(function () {
  function getVersionLabel(version) {
    return version.verbose_name || version.slug || version.ref || 'unknown';
  }

  function getVersionUrl(current, target) {
    const targetUrl = target && target.urls && target.urls.documentation;
    if (!targetUrl) return undefined;

    const currentUrl = current && current.urls && current.urls.documentation;
    if (!currentUrl) return targetUrl;

    try {
      const currentBase = new URL(currentUrl, window.location.href);
      const targetBase = new URL(targetUrl, window.location.href);

      if (!window.location.pathname.startsWith(currentBase.pathname)) {
        return targetBase.href;
      }

      const suffix = window.location.pathname.slice(currentBase.pathname.length);
      targetBase.pathname = joinPaths(targetBase.pathname, suffix);
      targetBase.search = window.location.search;
      targetBase.hash = window.location.hash;
      return targetBase.href;
    } catch {
      return targetUrl;
    }
  }

  function joinPaths(base, suffix) {
    const normalizedBase = base.endsWith('/') ? base : `${base}/`;
    const normalizedSuffix = suffix.startsWith('/') ? suffix.slice(1) : suffix;
    return `${normalizedBase}${normalizedSuffix}`;
  }

  function addVersionSelector(data) {
    const versions = data && data.versions && Array.isArray(data.versions.active) ? data.versions.active : [];
    const current = data && data.versions && data.versions.current;
    if (!current || versions.length < 2 || document.querySelector('.rtd-version-select')) return;

    const label = document.createElement('label');
    label.className = 'rtd-version-select';
    label.title = 'Select documentation version';

    const text = document.createElement('span');
    text.className = 'sr-only';
    text.textContent = 'Select documentation version';
    label.append(text);

    const select = document.createElement('select');
    select.autocomplete = 'off';

    for (const version of versions) {
      const url = getVersionUrl(current, version);
      if (!url) continue;

      const option = document.createElement('option');
      option.value = url;
      option.textContent = getVersionLabel(version);
      option.selected = version.slug === current.slug;
      select.append(option);
    }

    if (select.options.length < 2) return;

    select.addEventListener('change', function () {
      if (select.value) window.location.href = select.value;
    });

    label.append(select);

    const headerControls = document.querySelector('.right-group') || document.querySelector('.header .sl-flex.print\\:hidden');
    if (!headerControls) return;

    headerControls.prepend(label);
  }

  document.addEventListener('readthedocs-addons-data-ready', function (event) {
    const detail = event.detail;
    const data = detail && typeof detail.data === 'function' ? detail.data() : undefined;
    addVersionSelector(data);
  });
})();
