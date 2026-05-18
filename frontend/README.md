# Telegram Football Manager - Frontend

Frontend application for Telegram Football Manager built with Vite and vanilla JavaScript.

## Features

- **HTML5 Canvas Rendering**: 2D match visualization with smooth animations
- **Telegram Web App Integration**: Native Telegram Web App SDK integration
- **Mobile-First Design**: Optimized for mobile devices with touch controls
- **Responsive Layout**: Supports both portrait and landscape orientations
- **Real-Time Updates**: WebSocket connection for live match events
- **Fast Development**: Vite for instant HMR and optimized builds

## Tech Stack

- **Build Tool**: Vite 5.x
- **Language**: Vanilla JavaScript (ES6+)
- **Rendering**: HTML5 Canvas API
- **Platform**: Telegram Web App SDK
- **Communication**: Fetch API + WebSocket

## Project Structure

```
frontend/
├── src/
│   ├── main.js              # Application entry point
│   ├── style.css            # Global styles
│   ├── telegram-init.js     # Telegram Web App initialization
│   ├── match-renderer.js    # 2D match rendering engine
│   ├── api-client.js        # Backend API client
│   └── navigation.js        # Navigation manager
├── public/                  # Static assets
├── index.html               # HTML template
├── vite.config.js           # Vite configuration
├── package.json             # Dependencies
└── README.md                # This file
```

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- Backend server running on `http://localhost:8000`

### Installation

1. Install dependencies:
```bash
npm install
```

2. Start development server:
```bash
npm run dev
```

The application will be available at `http://localhost:3000`.

### Development

The development server includes:
- Hot Module Replacement (HMR)
- Proxy to FastAPI backend (`/api` → `http://localhost:8000/api`)
- WebSocket proxy (`/ws` → `ws://localhost:8000/ws`)

### Building for Production

Build optimized production bundle:
```bash
npm run build
```

Output will be in the `dist/` directory.

Preview production build:
```bash
npm run preview
```

## Configuration

### Vite Configuration

The `vite.config.js` file includes:

- **Development Server**: Port 3000 with backend proxy
- **Build Optimization**: Code splitting, minification, asset optimization
- **WebSocket Support**: Proxy for real-time match events

### Backend Proxy

API requests are automatically proxied to the FastAPI backend:

- `/api/*` → `http://localhost:8000/api/*`
- `/ws/*` → `ws://localhost:8000/ws/*`

Update `vite.config.js` if your backend runs on a different port.

## Telegram Web App Integration

### Testing Locally

To test the Telegram Web App locally:

1. Use ngrok or similar tool to expose your local server:
```bash
ngrok http 3000
```

2. Set the Web App URL in BotFather to the ngrok URL

3. Open the bot in Telegram and launch the Web App

### Telegram Web App Features

- **Theme Integration**: Automatically adapts to Telegram theme (light/dark)
- **Haptic Feedback**: Touch feedback for better UX
- **Main Button**: Telegram's native main button for primary actions
- **Back Button**: Native back button integration
- **Viewport Management**: Handles keyboard and viewport changes

## Canvas Rendering

### Match Renderer

The `MatchRenderer` class handles 2D match visualization:

- **Pitch Rendering**: Top-down 2D pitch with markings
- **Player Animation**: Smooth player movement and actions
- **Ball Physics**: Realistic ball movement
- **Event Processing**: Time-stamped match events
- **Playback Control**: 1x, 2x, 4x, or instant playback

### Performance

Target performance:
- 30+ FPS on mid-range mobile devices
- < 100ms event processing latency
- Responsive canvas resizing

## API Client

The `APIClient` class provides methods for:

- User management
- Career operations
- Squad management
- Player search
- Match simulation
- Tactics management
- Transfer operations
- WebSocket connections

### Authentication

Requests include Telegram init data in the `X-Telegram-Init-Data` header for backend authentication.

## Navigation

Bottom navigation with 5 main sections:

1. **Home** (🏠): Dashboard and overview
2. **Squad** (👥): Squad management
3. **Tactics** (📋): Formation and tactics
4. **Transfers** (💰): Transfer market
5. **Match** (⚽): Match center

## Styling

### CSS Variables

The app uses CSS variables for theming:

- Colors: Pitch green, team colors, Telegram theme colors
- Spacing: Consistent spacing scale
- Typography: Responsive font sizes
- Touch targets: Minimum 44x44px

### Responsive Design

- Mobile-first approach
- Portrait and landscape support
- Touch-friendly controls (44x44px minimum)
- Adaptive layouts

### Dark Mode

Automatically adapts to Telegram theme:
- Light mode: Standard colors
- Dark mode: Adjusted colors for better contrast

## Browser Support

- Modern browsers with ES6+ support
- iOS Safari 14+
- Android Chrome 90+
- Desktop browsers (Chrome, Firefox, Safari, Edge)

## Development Tips

### Debugging

Access the app instance in browser console:
```javascript
window.TFM // Main app instance
```

### Hot Reload

Vite provides instant HMR for:
- JavaScript modules
- CSS styles
- HTML changes

### Canvas Debugging

The canvas automatically resizes on:
- Window resize
- Orientation change
- Telegram viewport change

## Deployment

### Static Hosting

The built application is a static site that can be hosted on:

- Vercel
- Netlify
- GitHub Pages
- AWS S3 + CloudFront
- Any static hosting service

### Environment Variables

No environment variables needed - all configuration is in `vite.config.js`.

### Backend Integration

Ensure the backend API is accessible from the deployed frontend. Update CORS settings in the FastAPI backend if needed.

## Performance Optimization

### Build Optimizations

- Code splitting (match renderer, Telegram SDK)
- Minification (Terser)
- Asset optimization
- Tree shaking

### Runtime Optimizations

- Canvas object pooling
- Event throttling
- Lazy loading
- Efficient rendering loop

## Troubleshooting

### Canvas not rendering

- Check canvas element exists
- Verify canvas size is set correctly
- Check browser console for errors

### API requests failing

- Verify backend is running
- Check proxy configuration in `vite.config.js`
- Inspect network tab for request details

### Telegram Web App not working

- Ensure Telegram Web App SDK is loaded
- Check `window.Telegram.WebApp` is available
- Test in actual Telegram app (not browser)

## Contributing

When adding new features:

1. Follow existing code structure
2. Add JSDoc comments
3. Test on mobile devices
4. Ensure responsive design
5. Update this README if needed

## License

Part of the Telegram Football Manager project.
