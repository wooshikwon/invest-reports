// 미니 앱의 진입점이다. 모듈을 불러온 뒤 0.8의 한 파일 스크립트가 위에서부터 걸던 순서대로 손길과 값 받기를 건다.
import "./styles.css";
import { initPress } from "./shared/press";
import { initTelegram } from "./shared/telegram";
import { initPull } from "./shared/pull";
import { initRoute, initHistory, initPopstate, present } from "./shared/route";
import { initChrome } from "./shared/chrome";
import { initData } from "./shared/data";
import { initLive } from "./shared/live";

initPress();
initTelegram();
initPull();
initRoute();
initChrome();
initHistory();
initData();
initLive();
initPopstate();
present();
