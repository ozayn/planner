import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Image,
  FlatList,
  SafeAreaView,
  StatusBar,
} from 'react-native';
import Icon from 'react-native-vector-icons/MaterialIcons';
import LinearGradient from 'react-native-linear-gradient';

// API Configuration
const API_BASE_URL = 'http://localhost:5001/api';

// Color scheme matching web app
const colors = {
  primaryPastel: '#E8F4FD',
  secondaryPastel: '#F0F8E8',
  accentPastel: '#FFF0F5',
  neutralPastel: '#F8F9FA',
  textSoft: '#6B7280',
  textPrimary: '#374151',
  borderSoft: '#E5E7EB',
  white: '#FFFFFF',
};

const EventPlannerApp = () => {
  const [cities, setCities] = useState([]);
  const [selectedCity, setSelectedCity] = useState(null);
  const [selectedTimeRange, setSelectedTimeRange] = useState('today');
  const [selectedEventType, setSelectedEventType] = useState('');
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadCities();
  }, []);

  useEffect(() => {
    if (selectedCity) {
      loadEvents();
    }
  }, [selectedCity, selectedTimeRange, selectedEventType]);

  const loadCities = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/cities`);
      const data = await response.json();
      setCities(data);
    } catch (error) {
      console.error('Error loading cities:', error);
    }
  };

  const loadEvents = async () => {
    if (!selectedCity) return;
    
    setLoading(true);
    try {
      const params = new URLSearchParams({
        city_id: selectedCity.id,
        time_range: selectedTimeRange,
        event_type: selectedEventType,
      });
      
      const response = await fetch(`${API_BASE_URL}/events?${params}`);
      const data = await response.json();
      setEvents(data);
    } catch (error) {
      console.error('Error loading events:', error);
    } finally {
      setLoading(false);
    }
  };

  const timeRanges = [
    { key: 'today', label: 'Today', icon: 'today' },
    { key: 'tomorrow', label: 'Tomorrow', icon: 'schedule' },
    { key: 'this_week', label: 'This Week', icon: 'date-range' },
    { key: 'this_month', label: 'This Month', icon: 'calendar-month' },
  ];

  const eventTypes = [
    { key: '', label: 'All', icon: 'apps' },
    { key: 'tours', label: 'Tours', icon: 'directions-walk' },
    { key: 'exhibitions', label: 'Exhibitions', icon: 'palette' },
    { key: 'festivals', label: 'Festivals', icon: 'celebration' },
    { key: 'photowalks', label: 'Photowalks', icon: 'camera-alt' },
  ];

  const renderCitySelector = () => (
    <View style={styles.selectorContainer}>
      <Text style={styles.selectorLabel}>
        <Icon name="location-on" size={16} color={colors.textPrimary} /> City
      </Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.cityScroll}>
        {cities.map((city) => (
          <TouchableOpacity
            key={city.id}
            style={[
              styles.cityButton,
              selectedCity?.id === city.id && styles.cityButtonActive,
            ]}
            onPress={() => setSelectedCity(city)}
          >
            <Text
              style={[
                styles.cityButtonText,
                selectedCity?.id === city.id && styles.cityButtonTextActive,
              ]}
            >
              {city.display_name}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>
    </View>
  );

  const renderTimeFilter = () => (
    <View style={styles.selectorContainer}>
      <Text style={styles.selectorLabel}>
        <Icon name="schedule" size={16} color={colors.textPrimary} /> Time
      </Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.filterScroll}>
        {timeRanges.map((range) => (
          <TouchableOpacity
            key={range.key}
            style={[
              styles.filterButton,
              selectedTimeRange === range.key && styles.filterButtonActive,
            ]}
            onPress={() => setSelectedTimeRange(range.key)}
          >
            <Icon
              name={range.icon}
              size={16}
              color={selectedTimeRange === range.key ? colors.textPrimary : colors.textSoft}
            />
            <Text
              style={[
                styles.filterButtonText,
                selectedTimeRange === range.key && styles.filterButtonTextActive,
              ]}
            >
              {range.label}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>
    </View>
  );

  const renderEventTypeFilter = () => (
    <View style={styles.selectorContainer}>
      <Text style={styles.selectorLabel}>
        <Icon name="filter-list" size={16} color={colors.textPrimary} /> Events
      </Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.filterScroll}>
        {eventTypes.map((type) => (
          <TouchableOpacity
            key={type.key}
            style={[
              styles.filterButton,
              selectedEventType === type.key && styles.filterButtonActive,
            ]}
            onPress={() => setSelectedEventType(type.key)}
          >
            <Icon
              name={type.icon}
              size={16}
              color={selectedEventType === type.key ? colors.textPrimary : colors.textSoft}
            />
            <Text
              style={[
                styles.filterButtonText,
                selectedEventType === type.key && styles.filterButtonTextActive,
              ]}
            >
              {type.label}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>
    </View>
  );

  const renderEventCard = ({ item }) => {
    const startTime = item.start_time ? new Date(`2000-01-01T${item.start_time}`).toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    }) : '';
    
    const endTime = item.end_time ? new Date(`2000-01-01T${item.end_time}`).toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    }) : '';
    
    const timeDisplay = startTime && endTime ? `${startTime} - ${endTime}` : startTime || '';

    return (
      <View style={styles.eventCard}>
        {item.image_url && (
          <Image source={{ uri: item.image_url }} style={styles.eventImage} />
        )}
        <View style={styles.eventContent}>
          <Text style={styles.eventTitle}>{item.title}</Text>
          
          <View style={styles.eventMeta}>
            <View style={styles.metaItem}>
              <Icon name="calendar-today" size={14} color={colors.textSoft} />
              <Text style={styles.metaText}>
                {new Date(item.start_date).toLocaleDateString()}
              </Text>
            </View>
            
            {timeDisplay && (
              <View style={styles.metaItem}>
                <Icon name="schedule" size={14} color={colors.textSoft} />
                <Text style={styles.metaText}>{timeDisplay}</Text>
              </View>
            )}
            
            {item.venue_name && (
              <View style={styles.metaItem}>
                <Icon name="location-on" size={14} color={colors.textSoft} />
                <Text style={styles.metaText}>{item.venue_name}</Text>
              </View>
            )}
          </View>
          
          {item.description && (
            <Text style={styles.eventDescription} numberOfLines={3}>
              {item.description}
            </Text>
          )}
          
          <View style={styles.eventActions}>
            <TouchableOpacity style={styles.actionButton}>
              <Icon name="favorite-border" size={20} color={colors.textSoft} />
            </TouchableOpacity>
            <TouchableOpacity style={styles.actionButton}>
              <Icon name="event" size={20} color={colors.textSoft} />
            </TouchableOpacity>
            {item.url && (
              <TouchableOpacity style={styles.actionButton}>
                <Icon name="open-in-new" size={20} color={colors.textSoft} />
              </TouchableOpacity>
            )}
          </View>
        </View>
      </View>
    );
  };

  const renderEmptyState = () => (
    <View style={styles.emptyState}>
      <Icon name="event-busy" size={48} color={colors.textSoft} />
      <Text style={styles.emptyStateTitle}>No events found</Text>
      <Text style={styles.emptyStateText}>
        Try selecting a different city or time range
      </Text>
    </View>
  );

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor={colors.primaryPastel} />
      
      <LinearGradient
        colors={[colors.primaryPastel, colors.secondaryPastel]}
        style={styles.header}
      >
        <Text style={styles.headerTitle}>Event Planner</Text>
        <Text style={styles.headerSubtitle}>Discover amazing events in your city</Text>
      </LinearGradient>
      
      <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
        <View style={styles.controls}>
          {renderCitySelector()}
          {renderTimeFilter()}
          {renderEventTypeFilter()}
        </View>
        
        {loading ? (
          <View style={styles.loading}>
            <Text style={styles.loadingText}>Loading events...</Text>
          </View>
        ) : events.length > 0 ? (
          <FlatList
            data={events}
            renderItem={renderEventCard}
            keyExtractor={(item) => item.id.toString()}
            scrollEnabled={false}
            showsVerticalScrollIndicator={false}
          />
        ) : (
          renderEmptyState()
        )}
      </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.neutralPastel,
  },
  header: {
    padding: 20,
    paddingTop: 10,
  },
  headerTitle: {
    fontSize: 28,
    fontWeight: '500',
    color: colors.textPrimary,
    textAlign: 'center',
    marginBottom: 4,
  },
  headerSubtitle: {
    fontSize: 16,
    color: colors.textSoft,
    textAlign: 'center',
  },
  content: {
    flex: 1,
  },
  controls: {
    backgroundColor: colors.white,
    margin: 16,
    borderRadius: 16,
    padding: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 3,
  },
  selectorContainer: {
    marginBottom: 16,
  },
  selectorLabel: {
    fontSize: 16,
    fontWeight: '500',
    color: colors.textPrimary,
    marginBottom: 8,
  },
  cityScroll: {
    flexDirection: 'row',
  },
  cityButton: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: colors.white,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    marginRight: 8,
  },
  cityButtonActive: {
    backgroundColor: colors.accentPastel,
    borderColor: colors.accentPastel,
  },
  cityButtonText: {
    fontSize: 14,
    color: colors.textSoft,
  },
  cityButtonTextActive: {
    color: colors.textPrimary,
  },
  filterScroll: {
    flexDirection: 'row',
  },
  filterButton: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    backgroundColor: colors.white,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    marginRight: 6,
  },
  filterButtonActive: {
    backgroundColor: colors.secondaryPastel,
    borderColor: colors.secondaryPastel,
  },
  filterButtonText: {
    fontSize: 12,
    color: colors.textSoft,
    marginLeft: 4,
  },
  filterButtonTextActive: {
    color: colors.textPrimary,
  },
  eventCard: {
    backgroundColor: colors.white,
    borderRadius: 16,
    margin: 16,
    marginTop: 0,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 3,
    overflow: 'hidden',
  },
  eventImage: {
    width: '100%',
    height: 200,
    resizeMode: 'cover',
  },
  eventContent: {
    padding: 16,
  },
  eventTitle: {
    fontSize: 18,
    fontWeight: '500',
    color: colors.textPrimary,
    marginBottom: 8,
  },
  eventMeta: {
    marginBottom: 8,
  },
  metaItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
  },
  metaText: {
    fontSize: 12,
    color: colors.textSoft,
    marginLeft: 6,
  },
  eventDescription: {
    fontSize: 14,
    color: colors.textSoft,
    lineHeight: 20,
    marginBottom: 12,
  },
  eventActions: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    gap: 8,
  },
  actionButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colors.neutralPastel,
    justifyContent: 'center',
    alignItems: 'center',
  },
  emptyState: {
    alignItems: 'center',
    padding: 40,
  },
  emptyStateTitle: {
    fontSize: 18,
    fontWeight: '500',
    color: colors.textPrimary,
    marginTop: 16,
    marginBottom: 8,
  },
  emptyStateText: {
    fontSize: 14,
    color: colors.textSoft,
    textAlign: 'center',
  },
  loading: {
    alignItems: 'center',
    padding: 40,
  },
  loadingText: {
    fontSize: 16,
    color: colors.textSoft,
  },
});

export default EventPlannerApp;
