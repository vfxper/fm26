# Frontend Development Guide

This guide provides detailed information for developers working on the Telegram Football Manager frontend.

## Architecture Overview

### Module Structure

```
src/
├── main.js              # Application entry point and initialization
├── style.css            # Global styles and CSS variables
├── telegram-init.js     # Telegram Web App SDK wrapper
├── match-renderer.js    # 2D Canvas match rendering engine
├── api-client.js        # Backend API communication
├── navigation.js        # Page navigation and routing
└── demo-match-data.js   # Sample data for testing
```

### Key Components

#### 1. Main Application (main.js)

Entry point that:
- Initializes Telegram Web App
- Sets up API client
- Creates match renderer
- Manages application state
- Handles window events (resize, orientation)

#### 2. Telegram Integration (telegram-init.js)

Provides functions for:
- Web App initialization
- Theme management
- Main/Back button control
- Popups and alerts
- Haptic feedback
- User data access

#### 3. Match Renderer (match-renderer.js)

Canvas-based 2D match visualization:
- Pitch rendering with markings
- Player and ball animation
- Event processing
- Playback controls (pause, speed)
- Responsive scaling

#### 4. API Client (api-client.js)

HTTP and WebSocket communication:
- RESTful API methods
- WebSocket for real-time events
- Authentication headers
- Error handling

#### 5. Navigation (navigation.js)

Bottom navigation management:
- Page routing
- Active state management
- Notification badges
- Haptic feedback

## Development Workflow

### Setup

1. Install dependencies:
```bash
npm install
```

2. Start dev server:
```bash
npm run dev
```

3. Open http://localhost:3000

### Hot Module Replacement

Vite provides instant HMR for:
- JavaScript changes
- CSS updates
- HTML modifications

No page reload needed in most cases.

### Testing with Telegram

#### Local Testing

1. Expose local server with ngrok:
```bash
ngrok http 3000
```

2. Set Web App URL in BotFather:
```
/setmenubutton
[Select your bot]
[Paste ngrok URL]
```

3. Open bot in Telegram and launch Web App

#### Debugging

- Use Telegram Desktop for easier debugging
- Enable Developer Tools in Telegram Desktop
- Use `window.TFM` to access app instance in console

### Backend Integration

#### API Proxy

Development server proxies API requests:
- `/api/*` → `http://localhost:8000/api/*`
- `/ws/*` → `ws://localhost:8000/ws/*`

Update `vite.config.js` if backend runs on different port.

#### Authentication

Requests include Telegram init data:
```javascript
headers: {
  'X-Telegram-Init-Data': window.Telegram.WebApp.initData
}
```

Backend validates this data to authenticate users.

## Canvas Rendering

### Match Renderer API

#### Loading Match Data

```javascript
const matchRenderer = new MatchRenderer(canvas);

matchRenderer.loadMatch({
  homeTeam: {
    name: 'Team A',
    color: '#ff0000',
    players: [
      { id: 1, number: 1, name: 'Player 1', x: 10, y: 34 },
      // ... more players
    ],
  },
  awayTeam: {
    name: 'Team B',
    color: '#0000ff',
    players: [
      { id: 12, number: 1, name: 'Player 12', x: 95, y: 34 },
      // ... more players
    ],
  },
  events: [
    {
      minute: 5,
      second: 23,
      event_type: 'PASS',
      team: 'home',
      player_id: 7,
      position: { x: 70, y: 30 },
      success: true,
    },
    // ... more events
  ],
});
```

#### Playback Control

```javascript
// Start playback
matchRenderer.start();

// Pause
matchRenderer.pause();

// Resume
matchRenderer.resume();

// Stop
matchRenderer.stop();

// Set speed (1x, 2x, 4x, or 0 for instant)
matchRenderer.setSpeed(2);
```

#### Coordinate System

- Pitch dimensions: 105m × 68m
- Origin (0, 0) at top-left corner
- Home team attacks left to right
- Away team attacks right to left

#### Event Types

Supported event types:
- `KICKOFF`: Match start
- `PASS`: Player pass
- `SHOT`: Shot on goal
- `GOAL`: Goal scored
- `TACKLE`: Tackle attempt
- `FOUL`: Foul committed
- `CARD`: Yellow/red card
- `SUBSTITUTION`: Player substitution
- `HALF_TIME`: End of first half
- `FULL_TIME`: End of match

### Performance Optimization

#### Canvas Best Practices

1. **Use requestAnimationFrame**: Smooth 60 FPS rendering
2. **Minimize draw calls**: Batch similar operations
3. **Clear only changed areas**: Use dirty rectangles
4. **Cache static elements**: Pre-render pitch markings
5. **Object pooling**: Reuse objects instead of creating new ones

#### Mobile Optimization

1. **Limit canvas size**: Max 2048×2048 on mobile
2. **Reduce particle effects**: Fewer particles on low-end devices
3. **Throttle events**: Process events at reasonable rate
4. **Use CSS transforms**: Hardware-accelerated animations

## Styling Guidelines

### CSS Variables

Use CSS variables for consistency:

```css
:root {
  --pitch-green: #2d5016;
  --spacing-md: 16px;
  --font-size-md: 15px;
  --touch-target-min: 44px;
}
```

### Responsive Design

Mobile-first approach:

```css
/* Mobile (default) */
.element {
  font-size: 14px;
}

/* Tablet and up */
@media (min-width: 768px) {
  .element {
    font-size: 16px;
  }
}
```

### Touch Targets

Minimum 44×44px for all interactive elements:

```css
.button {
  min-width: 44px;
  min-height: 44px;
}
```

### Dark Mode

Use Telegram theme colors:

```css
.element {
  background-color: var(--tg-theme-bg-color, #ffffff);
  color: var(--tg-theme-text-color, #000000);
}
```

## API Integration

### Making Requests

```javascript
const apiClient = new APIClient('/api');

// GET request
const user = await apiClient.get('/users/123');

// POST request
const career = await apiClient.post('/careers', {
  manager_name: 'John Doe',
  club_id: 1,
});

// With query parameters
const players = await apiClient.get('/players/search', {
  position: 'ST',
  min_ca: 150,
  max_age: 25,
});
```

### WebSocket Connection

```javascript
const apiClient = new APIClient('/api');

// Connect to match WebSocket
apiClient.connectMatchWebSocket(
  matchId,
  (data) => {
    // Handle incoming message
    console.log('Match event:', data);
  },
  (error) => {
    // Handle error
    console.error('WebSocket error:', error);
  },
  (event) => {
    // Handle close
    console.log('WebSocket closed:', event.code);
  }
);

// Send message
apiClient.sendWebSocketMessage({
  action: 'pause',
});

// Close connection
apiClient.closeWebSocket();
```

### Error Handling

```javascript
try {
  const data = await apiClient.get('/endpoint');
} catch (error) {
  if (error instanceof APIError) {
    console.error('API Error:', error.status, error.message);
    // Show user-friendly error message
  } else {
    console.error('Network Error:', error);
    // Show network error message
  }
}
```

## Navigation

### Adding New Pages

1. Create page renderer function:

```javascript
function renderMyPage() {
  const overlay = document.getElementById('ui-overlay');
  overlay.innerHTML = `
    <div class="page-container">
      <h1>My Page</h1>
      <!-- Page content -->
    </div>
  `;
}
```

2. Register page:

```javascript
navigationManager.registerPage('mypage', renderMyPage);
```

3. Add navigation item in HTML:

```html
<div class="nav-item" data-page="mypage">
  <div class="nav-icon">🎯</div>
  <div class="nav-label">My Page</div>
</div>
```

### Notification Badges

```javascript
// Show badge
navigationManager.showNotificationBadge('transfers', 5);

// Hide badge
navigationManager.hideNotificationBadge('transfers');
```

## Testing

### Manual Testing Checklist

- [ ] Canvas renders correctly on different screen sizes
- [ ] Touch interactions work smoothly
- [ ] Navigation between pages works
- [ ] API requests succeed
- [ ] WebSocket connection establishes
- [ ] Telegram theme integration works
- [ ] Haptic feedback triggers
- [ ] Orientation changes handled correctly

### Browser Testing

Test on:
- iOS Safari (iPhone, iPad)
- Android Chrome
- Telegram Desktop (Windows, macOS, Linux)
- Telegram Mobile (iOS, Android)

### Performance Testing

Monitor:
- Canvas FPS (target: 30+ FPS)
- Memory usage (watch for leaks)
- Network requests (minimize count)
- Bundle size (keep under 500KB)

## Build and Deployment

### Production Build

```bash
npm run build
```

Output in `dist/` directory.

### Build Optimization

Vite automatically:
- Minifies JavaScript (Terser)
- Optimizes CSS
- Compresses assets
- Generates source maps (optional)
- Code splits (manual chunks configured)

### Deployment Checklist

- [ ] Build completes without errors
- [ ] Test production build locally (`npm run preview`)
- [ ] Verify all assets load correctly
- [ ] Check bundle size (< 500KB recommended)
- [ ] Test on actual Telegram Web App
- [ ] Verify backend API connectivity
- [ ] Check CORS configuration

## Common Issues

### Canvas Not Rendering

**Problem**: Canvas appears blank

**Solutions**:
1. Check canvas element exists in DOM
2. Verify canvas width/height are set
3. Check for JavaScript errors in console
4. Ensure `resize()` was called

### API Requests Failing

**Problem**: API requests return errors

**Solutions**:
1. Verify backend is running
2. Check proxy configuration in `vite.config.js`
3. Inspect network tab for request details
4. Verify authentication headers

### Telegram Web App Not Working

**Problem**: Telegram features not available

**Solutions**:
1. Ensure SDK script is loaded
2. Check `window.Telegram.WebApp` exists
3. Test in actual Telegram app (not browser)
4. Verify Web App URL is set correctly in BotFather

### Performance Issues

**Problem**: Low FPS or laggy animations

**Solutions**:
1. Reduce canvas size
2. Limit particle effects
3. Optimize draw calls
4. Use object pooling
5. Profile with browser DevTools

## Code Style

### JavaScript

- Use ES6+ features
- Prefer `const` over `let`
- Use arrow functions for callbacks
- Add JSDoc comments for functions
- Use meaningful variable names

### CSS

- Use CSS variables for theming
- Follow BEM naming convention
- Mobile-first media queries
- Avoid `!important`
- Group related properties

### File Organization

- One class per file
- Group related functions
- Export at end of file
- Import at top of file

## Resources

### Documentation

- [Vite Documentation](https://vitejs.dev/)
- [Telegram Web App API](https://core.telegram.org/bots/webapps)
- [Canvas API](https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API)
- [WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)

### Tools

- [ngrok](https://ngrok.com/) - Local tunnel for testing
- [Chrome DevTools](https://developer.chrome.com/docs/devtools/) - Debugging
- [Lighthouse](https://developers.google.com/web/tools/lighthouse) - Performance auditing

## Getting Help

If you encounter issues:

1. Check this guide
2. Review existing code examples
3. Check browser console for errors
4. Test in different browsers/devices
5. Ask team members for help
