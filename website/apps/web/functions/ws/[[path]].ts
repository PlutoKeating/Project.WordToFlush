// 原样转发（含 WebSocket Upgrade）到 wordtoflush-api Worker（Service Binding，见 wrangler.toml）
export const onRequest: PagesFunction<{ API: Fetcher }> = ({ request, env }) => env.API.fetch(request)
