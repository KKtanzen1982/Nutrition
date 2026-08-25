import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { VitePWA } from 'vite-plugin-pwa';
export default defineConfig({
    plugins: [
        vue(),
        VitePWA({
            registerType: 'autoUpdate',
            devOptions: { enabled: true },
            includeAssets: ['icons/BLOCK_7_apple_touch_icon.png'],
            manifest: {
                name: '飲食管理系統',
                short_name: '飲食管理',
                description: '雙人飲食與體態管理：體重、運動、週菜單推薦、購物清單',
                lang: 'zh-Hant',
                start_url: '/',
                scope: '/',
                display: 'standalone',
                theme_color: '#A13D3D',
                background_color: '#FBF5EA',
                icons: [
                    { src: '/icons/BLOCK_7_icon_192.png', sizes: '192x192', type: 'image/png', purpose: 'any' },
                    { src: '/icons/BLOCK_7_icon_512.png', sizes: '512x512', type: 'image/png', purpose: 'any' },
                    { src: '/icons/BLOCK_7_icon_maskable_512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
                ],
            },
            workbox: {
                globPatterns: ['**/*.{js,css,html,png,svg,ico}'],
                runtimeCaching: [
                    {
                        urlPattern: function (_a) {
                            var url = _a.url;
                            return url.pathname.startsWith('/api/');
                        },
                        method: 'GET',
                        handler: 'NetworkFirst',
                        options: {
                            cacheName: 'block7-api-cache',
                            networkTimeoutSeconds: 5,
                            expiration: { maxEntries: 100, maxAgeSeconds: 60 * 60 * 24 },
                            cacheableResponse: { statuses: [0, 200] },
                        },
                    },
                ],
            },
        }),
    ],
});
