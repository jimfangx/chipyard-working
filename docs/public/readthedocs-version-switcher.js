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

  function createVersionSelector(data, id) {
    const versions = data && data.versions && Array.isArray(data.versions.active) ? data.versions.active : [];
    const current = data && data.versions && data.versions.current;
    if (!current || versions.length < 2) return undefined;

    const label = document.createElement('label');
    label.className = 'rtd-version-select';
    label.dataset.rtdVersionSelect = id;
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
    return label;
  }

  function mountVersionSelector(data) {
    const targets = [
      ['desktop', document.querySelector('.right-group')],
      ['mobile', document.querySelector('.mobile-preferences')],
    ];

    let mounted = false;
    for (const [id, target] of targets) {
      if (!target || target.querySelector(`[data-rtd-version-select="${id}"]`)) continue;

      const selector = createVersionSelector(data, id);
      if (!selector) continue;

      target.prepend(selector);
      mounted = true;
    }
    return mounted;
  }

  function getReadTheDocsData(event) {
    const source = event && event.detail ? event.detail : window.ReadTheDocsEventData;
    return source && typeof source.data === 'function' ? source.data() : undefined;
  }

  function tryMountVersionSelector(event) {
    const data = getReadTheDocsData(event);
    if (!data) return false;
    return mountVersionSelector(data);
  }

  function retryMountVersionSelector(remaining) {
    if (tryMountVersionSelector() || remaining <= 0) return;
    window.setTimeout(function () {
      retryMountVersionSelector(remaining - 1);
    }, 250);
  }

  document.addEventListener('readthedocs-addons-data-ready', tryMountVersionSelector);

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      retryMountVersionSelector(20);
    });
  } else {
    retryMountVersionSelector(20);
  }
})();
