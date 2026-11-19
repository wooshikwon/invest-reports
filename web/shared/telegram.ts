// @ts-nocheck
export const tg = window.Telegram && window.Telegram.WebApp;
// 텔레그램 앱 안에서만 기기를 진동시킨다. 이슈 상자·지수 단추·바로가기 단추·지수 지도 칸을 누르거나 접기 상자를 펼치면 가벼운 충격 진동을 낸다.
// 당겨 새로고침은 새로 받기를 시작할 때 가벼운 충격 진동을, 다시 연 리포트를 다 그렸을 때 성공 알림 진동을 낸다.
// 접기, 목록으로 돌아가기는 진동하지 않는다. 지수와 예측 절에서 보는 카드와 날짜 레버로 고른 날짜, 이벤트 캘린더에서 보는 날짜,
// 미국 거시 지표에서 보는 지표, 이슈 그림에서 보는 그림이 바뀔 때마다 선택 변경 진동을 낸다.
// 브라우저에서는 진동하지 않는다.
export const haptic = (tg && tg.initData && tg.HapticFeedback) || null;
export const feelPress = () => haptic?.impactOccurred("light");
export const feelSlide = () => haptic?.selectionChanged();
export function initTelegram() {
  if (tg && tg.initData) {
    tg.ready();
    // 리포트를 처음부터 시트를 끝까지 올린 높이로 연다.
    tg.expand();
    // 휴대폰에서는 전체화면으로 연다. 데스크톱 텔레그램은 거절하고 시트 그대로 둔다.
    if (tg.requestFullscreen && tg.isVersionAtLeast?.("8.0") && !tg.isFullscreen) tg.requestFullscreen();
    if (tg.setBackgroundColor) tg.setBackgroundColor("#171719");
    if (tg.setHeaderColor) tg.setHeaderColor("#171719");
    // 좌우로 넘기는 몸짓이 조금 기울어도 시트가 내려가지 않게, 세로로 끌어 닫는 동작을 끈다.
    if (tg.disableVerticalSwipes) tg.disableVerticalSwipes();
    // 텔레그램은 문서를 열 때마다 위쪽 높이(`--top-inset`)의 두 값을 0으로 두었다가 조금 뒤에 알려 주므로, 다시 연 문서는 그사이 본문이 위로 올라갔다 내려온다.
    // 받은 두 값을 `sessionStorage`의 `insets`에 적어 두고, 같은 세션에서 다시 연 문서는 텔레그램이 알려 주기 전까지 적어 둔 값을 쓴다.
    const insets = JSON.parse(sessionStorage.getItem("insets") || "null");
    if (insets) {
      document.documentElement.style.setProperty("--tg-safe-area-inset-top", `${insets.safe}px`);
      document.documentElement.style.setProperty("--tg-content-safe-area-inset-top", `${insets.content}px`);
    }
    const keepInsets = () => sessionStorage.setItem("insets", JSON.stringify({ safe: tg.safeAreaInset.top, content: tg.contentSafeAreaInset.top }));
    tg.onEvent("safeAreaChanged", keepInsets);
    tg.onEvent("contentSafeAreaChanged", keepInsets);
    // 낮은 시트에서도 웹뷰는 시트를 끝까지 올린 높이로 그려지고 위쪽만 화면에 보인다. 보이는 높이는 `viewportStableHeight`이므로
    // 웹뷰 높이와의 차이를 `--offscreen`에 적고, 시트 높이가 바뀔 때마다 다시 적는다.
    const offscreen = () => {
      const hidden = tg.viewportStableHeight ? Math.max(0, innerHeight - tg.viewportStableHeight) : 0;
      document.documentElement.style.setProperty("--offscreen", `${hidden}px`);
    };
    offscreen();
    tg.onEvent("viewportChanged", offscreen);
    window.addEventListener("resize", offscreen);
  }
}
