(function () {
  function counterpartPath(pathname, targetLanguage) {
    var normalized = pathname.replace(/\\/g, "/");
    var match = normalized.match(/^\/(en|zh)(\/.*)?$/);

    if (match) {
      var currentLanguage = match[1];
      var rest = match[2] || "/introduction.html";
      if (currentLanguage === targetLanguage) {
        return normalized;
      }
      return "/" + targetLanguage + rest;
    }

    if (normalized.endsWith("/") || normalized.endsWith("/index.html")) {
      return "/" + targetLanguage + "/introduction.html";
    }

    return "/" + targetLanguage + "/introduction.html";
  }

  function currentLanguage(pathname) {
    if (pathname.indexOf("/zh/") !== -1) {
      return "zh";
    }
    if (pathname.indexOf("/en/") !== -1) {
      return "en";
    }
    return "";
  }

  function addLanguageSwitch() {
    var rightButtons = document.querySelector(".right-buttons");
    if (!rightButtons || document.querySelector(".language-switch")) {
      return;
    }

    var pathname = window.location.pathname;
    var active = currentLanguage(pathname);
    var switcher = document.createElement("nav");
    switcher.className = "language-switch";
    switcher.setAttribute("aria-label", "Language");

    [
      ["en", "EN"],
      ["zh", "中文"],
    ].forEach(function (item) {
      var code = item[0];
      var label = item[1];
      var link = document.createElement("a");
      link.href = counterpartPath(pathname, code) + window.location.search + window.location.hash;
      link.textContent = label;
      link.className = active === code ? "active" : "";
      switcher.appendChild(link);
    });

    rightButtons.insertBefore(switcher, rightButtons.firstChild);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", addLanguageSwitch);
  } else {
    addLanguageSwitch();
  }
})();
