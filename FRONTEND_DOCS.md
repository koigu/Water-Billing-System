# Water Billing System - Frontend Documentation

## Overview

The Water Billing System is a Progressive Web App (PWA) built with FastAPI backend and Jinja2 HTML templates. This documentation covers the frontend architecture, components, styling, and development guidelines for frontend developers.

## Architecture

### Tech Stack
- **Backend**: FastAPI (Python)
- **Templates**: Jinja2
- **Styling**: Vanilla CSS with responsive design
- **JavaScript**: ES6+ for PWA functionality
- **PWA Features**: Service Worker, Web App Manifest, IndexedDB

### File Structure
```
water-billing-system/
├── templates/
│   ├── index.html          # Main dashboard template
│   ├── login.html          # Admin login template
│   ├── customers.html      # Customers management page
│   ├── readings.html       # Meter readings page
│   └── invoices.html       # Invoices management page
├── static/
│   ├── manifest.json       # PWA manifest
│   ├── sw.js              # Service worker
│   ├── icon-192.png       # PWA icons (to be created)
│   └── icon-512.png       # PWA icons (to be created)
├── app/
│   └── main.py            # FastAPI application
└── requirements.txt       # Python dependencies
```

## Templates

### index.html - Main Dashboard

#### Structure
```html
<!DOCTYPE html>
<html>
<head>
    <!-- PWA meta tags -->
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="theme-color" content="#007bff">
    <link rel="manifest" href="/static/manifest.json">

    <!-- Title and styles -->
    <title>Water Billing System</title>
    <style>...</style>
</head>
<body>
    <!-- Main content sections -->
    <h1>Water Billing System</h1>

    <!-- Rate Configuration Section -->
    <!-- Customer Management Section -->
    <!-- Invoice Management Section -->

    <!-- PWA JavaScript -->
    <script>...</script>
</body>
</html>
```

#### Key Sections

**Rate Configuration**
- Displays current rate mode and value
- Admin-only form for updating rates
- Test messaging functionality

**Customer Management**
- Form to create new customers
- Table view for desktop
- Card view for mobile devices
- Actions: Add readings, Generate invoices

**Invoice Management**
- Table view of all invoices
- Status tracking (pending, paid, overdue)
- Payment marking functionality

### login.html - Admin Authentication

Simple login form for admin access:
```html
<form method="post" action="/login">
    <input name="username" placeholder="Username" required />
    <input name="password" type="password" placeholder="Password" required />
    <button type="submit">Login</button>
</form>
```

## Styling

### CSS Architecture

The app uses a mobile-first responsive design with vanilla CSS:

#### Key CSS Classes

```css
/* Layout */
body {
    font-family: Arial, Helvetica, sans-serif;
    margin: 0;
    padding: 20px;
    max-width: 1200px;
    margin: 0 auto;
}

/* Forms */
form {
    margin-bottom: 20px;
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
}

form input, form select, form button {
    flex: 1;
    min-width: 150px;
    padding: 8px;
    border: 1px solid #ddd;
    border-radius: 4px;
}

/* Tables */
table {
    border-collapse: collapse;
    width: 100%;
    font-size: 14px;
}

th, td {
    border: 1px solid #ddd;
    padding: 8px;
    text-align: left;
}

/* Mobile Cards */
.mobile-card {
    display: none; /* Hidden on desktop */
    margin-bottom: 15px;
    padding: 15px;
    border: 1px solid #ddd;
    border-radius: 8px;
}

/* Responsive Breakpoints */
@media (max-width: 768px) {
    body { padding: 10px; }
    table { display: none; } /* Hide tables on mobile */
    .mobile-card { display: block; } /* Show cards on mobile */
    form {
        flex-direction: column;
    }
    form input, form select, form button {
        min-width: auto;
        width: 100%;
    }
}
```

### Design Principles

1. **Mobile-First**: Design optimized for mobile devices first
2. **Responsive**: Adapts to different screen sizes
3. **Accessible**: Proper contrast, touch targets, semantic HTML
4. **Progressive Enhancement**: Works without JavaScript, enhanced with it

## JavaScript Functionality

### Service Worker (sw.js)

Handles offline caching and app installation:

```javascript
const CACHE_NAME = 'water-billing-v1';
const urlsToCache = [
  '/',
  '/static/manifest.json',
  '/static/sw.js'
];

// Install event - cache essential files
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache))
  );
});

// Fetch event - serve from cache or network
self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => response || fetch(event.request))
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});
```

### Main App JavaScript (index.html)

#### Service Worker Registration
```javascript
if ('serviceWorker' in navigator) {
  window.addEventListener('load', function() {
    navigator.serviceWorker.register('/static/sw.js')
      .then(registration => console.log('SW registered'))
      .catch(err => console.log('SW registration failed:', err));
  });
}
```

#### Offline Data Storage
```javascript
// IndexedDB setup for offline data
let db;
const request = indexedDB.open('WaterBillingDB', 1);

request.onupgradeneeded = event => {
  db = event.target.result;
  if (!db.objectStoreNames.contains('customers')) {
    db.createObjectStore('customers', { keyPath: 'id' });
  }
  if (!db.objectStoreNames.contains('readings')) {
    db.createObjectStore('readings', { keyPath: 'id', autoIncrement: true });
  }
};

request.onsuccess = event => {
  db = event.target.result;
  console.log('IndexedDB initialized');
};

// Save data offline
function saveOffline(storeName, data) {
  if (!db) return;
  const transaction = db.transaction([storeName], 'readwrite');
  const store = transaction.objectStore(storeName);
  store.add(data);
}

// Sync when online
function syncData() {
  if (navigator.onLine) {
    console.log('Syncing data...');
    // Implement sync logic here
  }
}

window.addEventListener('online', syncData);
```

## PWA Features

### Web App Manifest (manifest.json)

```json
{
  "name": "Water Billing System",
  "short_name": "WaterBill",
  "description": "Manage water billing, customers, and invoices",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#007bff",
  "icons": [
    {
      "src": "/static/icon-192.png",
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "/static/icon-512.png",
      "sizes": "512x512",
      "type": "image/png"
    }
  ]
}
```

### Installation Criteria

The app meets PWA installation criteria:
- Served over HTTPS (in production)
- Has a web app manifest
- Has a service worker
- Responsive design

## Development Guidelines

### HTML Best Practices

1. **Semantic HTML**: Use proper heading hierarchy, semantic elements
2. **Accessibility**: Include alt text, proper labels, ARIA attributes
3. **Progressive Enhancement**: Ensure functionality works without JavaScript
4. **Mobile Optimization**: Use viewport meta tag, touch-friendly targets

### CSS Guidelines

1. **Mobile-First**: Write mobile styles first, then enhance for larger screens
2. **Flexbox/Grid**: Use modern layout techniques
3. **Consistent Spacing**: Use a spacing scale (8px increments)
4. **Performance**: Minimize CSS, use efficient selectors

### JavaScript Guidelines

1. **Progressive Enhancement**: Enhance, don't require JavaScript
2. **Error Handling**: Graceful degradation when features aren't supported
3. **Performance**: Minimize DOM manipulation, use event delegation
4. **Offline-First**: Design for offline usage, sync when online

### PWA Development

1. **Cache Strategy**: Cache app shell, lazy-load dynamic content
2. **Offline UX**: Provide feedback when offline, queue actions
3. **Sync Strategy**: Implement background sync for critical data
4. **Updates**: Handle service worker updates gracefully

## API Integration

### Backend Endpoints

The frontend interacts with these FastAPI endpoints:

#### GET Endpoints
- `GET /` - Main dashboard (renders template)
- `GET /login` - Login form
- `GET /logout` - Logout

#### POST Endpoints
- `POST /customers` - Create customer
- `POST /customers/{id}/readings` - Add meter reading
- `POST /invoices/generate/{id}` - Generate invoice
- `POST /invoices/{id}/pay` - Mark invoice paid
- `POST /rate` - Update rate configuration
- `POST /login` - Authenticate admin
- `POST /admin/send_test` - Send test message

### Data Flow

1. **Server-Side Rendering**: Templates rendered by FastAPI with Jinja2
2. **Form Submissions**: POST requests with form data
3. **Dynamic Updates**: JavaScript for offline storage and PWA features
4. **State Management**: Session-based authentication, template variables
5. **Invoice Generation Logic**: When an admin generates an invoice for a customer (via `POST /invoices/generate/{id}`), the backend:
    - Fetches the two most recent meter readings for the customer.
    - Calculates consumption (`Current Reading - Previous Reading`).
    - Retrieves the current rate per meter cubic.
    - Calculates the invoice amount (`Consumption * Rate per Meter Cubic`).
    - Creates a new invoice record with a "Pending" status.

    **Example Calculation:**
    - Previous Meter Reading: `1135 m³`
    - Current Meter Reading: `1150 m³`
    - Rate per Meter Cubic: `120 KES`

    1.  **Consumption**: `1150 - 1135 = 15 m³`
    2.  **Amount**: `15 m³ * 120 KES/m³ = 1800`

    The generated invoice will be for **1800 KES**.

This entire calculation happens on the backend, ensuring data integrity and consistent billing logic. The frontend is responsible for triggering this action and displaying the resulting invoice.


## Testing

### Frontend Testing Checklist

#### Visual Testing
- [ ] Desktop layout renders correctly
- [ ] Mobile layout adapts properly
- [ ] Tables hide on mobile, cards show
- [ ] Forms are touch-friendly on mobile

#### Functionality Testing
- [ ] Service worker registers successfully
- [ ] App can be installed on mobile
- [ ] Offline caching works
- [ ] IndexedDB storage functions
- [ ] Online sync triggers

#### Performance Testing
- [ ] Lighthouse PWA audit passes
- [ ] Page load times acceptable
- [ ] Memory usage reasonable
- [ ] Offline functionality works

## Deployment

### Build Process

1. **Static Assets**: Ensure icons are created and placed in `/static/`
2. **HTTPS**: Required for PWA installation in production
3. **Service Worker**: Update cache version for new deployments
4. **Testing**: Test PWA features in production environment

### Production Considerations

1. **CDN**: Consider using CDN for static assets
2. **Caching**: Implement proper cache headers
3. **Monitoring**: Monitor PWA installation rates, offline usage
4. **Updates**: Handle app updates gracefully

## Troubleshooting

### Common Issues

**Service Worker Not Registering**
- Check browser console for errors
- Ensure `/static/sw.js` is accessible
- Verify HTTPS in production

**PWA Not Installing**
- Check manifest.json syntax
- Ensure required icons exist
- Verify HTTPS and service worker

**Offline Not Working**
- Check service worker installation
- Verify cache storage
- Test IndexedDB functionality

**Mobile Layout Issues**
- Check viewport meta tag
- Test on actual mobile devices
- Verify media queries

## Future Enhancements

### Potential Improvements

1. **Component Architecture**: Break down into reusable components
2. **State Management**: Implement client-side state management
3. **Real-time Updates**: WebSocket integration for live updates
4. **Advanced PWA**: Background sync, push notifications
5. **Accessibility**: WCAG compliance improvements
6. **Performance**: Code splitting, lazy loading

### Technology Upgrades

1. **Framework Migration**: Consider React/Vue for complex interactions
2. **Build Tools**: Webpack/Vite for asset optimization
3. **CSS Framework**: Tailwind CSS for utility-first styling
4. **Testing Framework**: Jest/Cypress for comprehensive testing

---

This documentation provides a comprehensive guide for frontend developers working on the Water Billing System. The app follows modern web standards with a focus on mobile usability and offline functionality.
