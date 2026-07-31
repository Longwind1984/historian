(() => {
  const REQUEST_TYPE = "history-kb/weread-capture-selection/v1";
  const RESPONSE_TYPE = "history-kb/weread-capture-result/v1";
  const MAX_SELECTION_LENGTH = 2000;

  const clampSelection = (value) =>
    Array.from(String(value ?? "").replace(/\r\n?/g, "\n").trim())
      .slice(0, MAX_SELECTION_LENGTH)
      .join("");

  const currentLocator = () => {
    const path =
      `${window.location.pathname}${window.location.search}${window.location.hash}` ||
      "/";
    const title = document.title.trim();
    return (title ? `${title} · ${path}` : path).slice(0, 500);
  };

  const trustedSenderUrl = chrome.runtime.getURL("sidepanel.html");

  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (
      sender.id !== chrome.runtime.id ||
      sender.url !== trustedSenderUrl ||
      !message ||
      message.type !== REQUEST_TYPE ||
      message.version !== 1
    ) {
      return false;
    }

    const selection = clampSelection(window.getSelection()?.toString());
    sendResponse({
      type: RESPONSE_TYPE,
      version: 1,
      ok: true,
      payload: {
        title: document.title,
        url: window.location.href,
        locator: currentLocator(),
        selection,
        truncated:
          Array.from(String(window.getSelection()?.toString() ?? "").trim()).length >
          MAX_SELECTION_LENGTH
      }
    });
    return false;
  });
})();
