# Event Planner Mobile App

A React Native mobile app that provides the same functionality as the web version with a consistent minimal design.

## Features

- **Consistent Design**: Matches the web app's pastel color scheme and artistic fonts
- **City Selection**: Choose from major cities worldwide
- **Time Filtering**: Today, tomorrow, this week, this month
- **Event Types**: Tours, venues, exhibitions, festivals, photowalks
- **Calendar Integration**: Add events to device calendar
- **Responsive UI**: Optimized for mobile devices

## Design System

The mobile app uses the same design principles as the web version:

- **Pastel Colors**: Soft, gentle color palette
- **Artistic Fonts**: Playfair Display for headings, Inter for body text
- **Icon-Based UI**: Minimal text, maximum icon usage
- **Soft Shadows**: Subtle depth without harsh edges
- **Rounded Corners**: Gentle, friendly interface

## Installation

### Prerequisites

- Node.js (v14 or higher)
- React Native CLI
- Android Studio (for Android development)
- Xcode (for iOS development, macOS only)

### Setup

1. Navigate to the mobile directory:
```bash
cd mobile
```

2. Install dependencies:
```bash
npm install
```

3. For iOS (macOS only):
```bash
cd ios && pod install && cd ..
```

4. Start the Metro bundler:
```bash
npm start
```

5. Run on device/emulator:
```bash
# Android
npm run android

# iOS
npm run ios
```

## Configuration

The mobile app connects to the same backend API as the web version. Make sure the Flask backend is running on `http://localhost:5001` or update the `API_BASE_URL` in `App.js`.

## API Integration

The mobile app uses the same REST API endpoints as the web version:

- `GET /api/cities` - Get available cities
- `GET /api/events` - Get events with filters
- `GET /api/venues` - Get venues for a city
- `POST /api/calendar/add` - Add event to calendar

## Components

### Main Components

- **EventPlannerApp**: Main app component
- **CitySelector**: City selection interface
- **TimeFilter**: Time range filtering
- **EventTypeFilter**: Event type filtering
- **EventCard**: Individual event display
- **EmptyState**: No events found state

### Styling

The app uses StyleSheet for consistent styling with:

- Consistent color variables
- Responsive design patterns
- Touch-friendly button sizes
- Proper spacing and typography

## Features Comparison

| Feature | Web App | Mobile App |
|---------|---------|------------|
| City Selection | ✅ | ✅ |
| Time Filtering | ✅ | ✅ |
| Event Types | ✅ | ✅ |
| Calendar Integration | ✅ | ✅ |
| Responsive Design | ✅ | ✅ |
| Offline Support | ❌ | 🔄 Planned |
| Push Notifications | ❌ | 🔄 Planned |
| Location Services | ❌ | 🔄 Planned |

## Development

### Adding New Features

1. Update the API endpoints in the backend
2. Modify the mobile app to consume new endpoints
3. Update the UI components as needed
4. Test on both Android and iOS

### Styling Guidelines

- Use the defined color variables
- Maintain consistent spacing (8px grid)
- Use icons instead of text when possible
- Keep touch targets at least 44px
- Use soft shadows and rounded corners

## Deployment

### Android

1. Generate signed APK:
```bash
cd android
./gradlew assembleRelease
```

2. Upload to Google Play Store

### iOS

1. Archive the app in Xcode
2. Upload to App Store Connect
3. Submit for review

## Troubleshooting

### Common Issues

1. **Metro bundler not starting**: Clear cache with `npm start -- --reset-cache`
2. **Android build fails**: Check Android SDK and build tools
3. **iOS build fails**: Run `pod install` in ios directory
4. **API connection issues**: Verify backend is running and accessible

### Debug Mode

Enable debug mode by shaking the device or pressing `Cmd+D` (iOS) / `Cmd+M` (Android) to open the developer menu.

## Contributing

1. Follow the existing code style
2. Use TypeScript for new components
3. Add proper error handling
4. Test on both platforms
5. Update documentation

## License

Same as the main project.
