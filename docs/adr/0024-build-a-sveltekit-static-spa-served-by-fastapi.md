# Build a SvelteKit static SPA served by FastAPI

Artio's frontend uses SvelteKit for file-based routing and is built with the static adapter as a client-side SPA. The local FastAPI server serves the compiled assets and owns all backend and WebSocket behavior, while a Vite development server is used only during Artio development.
