import { defineConfig } from "vite";

// `web/`의 모듈을 묶어 저장소 맨 위에 `app.html`과 `assets/`를 만든다. GitHub Pages가 두 파일을 그대로 낸다.
export default defineConfig({
  root: "web",
  base: "./",
  publicDir: false,
  build: {
    outDir: "..",
    emptyOutDir: false,
    target: "es2022",
    modulePreload: { polyfill: false },
    rollupOptions: {
      input: "web/app.html",
      output: {
        entryFileNames: "assets/app-[hash].js",
        chunkFileNames: "assets/[name]-[hash].js",
        assetFileNames: "assets/[name]-[hash][extname]",
      },
    },
  },
});
