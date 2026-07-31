const enableActionSidePanel = () =>
  chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true });

chrome.runtime.onInstalled.addListener(() => {
  enableActionSidePanel().catch((error) => {
    console.error("无法启用工具栏 Side Panel：", error);
  });
});

chrome.runtime.onStartup.addListener(() => {
  enableActionSidePanel().catch((error) => {
    console.error("无法恢复工具栏 Side Panel：", error);
  });
});

enableActionSidePanel().catch((error) => {
  console.error("无法初始化工具栏 Side Panel：", error);
});
