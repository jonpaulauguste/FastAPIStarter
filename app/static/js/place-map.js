/**
 * Interactive Map for Place Detail Page
 * Uses Leaflet with OpenStreetMap tiles
 */

(function() {
    const mapContainer = document.getElementById('place-map');
    if (!mapContainer) return;

    const placeName = mapContainer.dataset.placeName || 'Campus Location';
    const placeLocation = mapContainer.dataset.placeLocation || '';

    // Default coordinates for UWI St. Augustine campus
    let lat = 10.6427;
    let lng = -61.3995;
    let zoom = 16;

    // Try to geocode the location string using Nominatim
    if (placeLocation) {
        const searchQuery = placeLocation + ', UWI, Trinidad and Tobago';
        fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(searchQuery)}`)
            .then(response => response.json())
            .then(data => {
                if (data && data.length > 0) {
                    lat = parseFloat(data[0].lat);
                    lng = parseFloat(data[0].lon);
                }
                initMap(lat, lng);
            })
            .catch(() => {
                initMap(lat, lng);
            });
    } else {
        initMap(lat, lng);
    }

    function initMap(centerLat, centerLng) {
        // Create map
        const map = L.map('place-map').setView([centerLat, centerLng], 16);

        // Add OpenStreetMap tile layer
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxZoom: 19
        }).addTo(map);

        // Add marker for the place
        const marker = L.marker([centerLat, centerLng]).addTo(map);
        marker.bindPopup(`<strong>${placeName}</strong><br>${placeLocation}`).openPopup();

        // Try to get user's location and show distance
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                function(position) {
                    const userLat = position.coords.latitude;
                    const userLng = position.coords.longitude;

                    // Add user location marker with custom icon
                    const userIcon = L.divIcon({
                        className: 'user-location-marker',
                        html: '<div style="background: #4285F4; width: 14px; height: 14px; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 6px rgba(0,0,0,0.3);"></div>',
                        iconSize: [20, 20],
                        iconAnchor: [10, 10]
                    });
                    
                    const userMarker = L.marker([userLat, userLng], { icon: userIcon }).addTo(map);
                    userMarker.bindPopup('📍 You are here');

                    // Calculate and display distance
                    const distance = getDistance(userLat, userLng, centerLat, centerLng);
                    const distanceDisplay = document.createElement('p');
                    distanceDisplay.style.cssText = 'font-size: 0.8rem; color: #666; margin-top: 4px;';
                    distanceDisplay.innerHTML = `📏 ${distance.toFixed(1)} km from your location`;
                    
                    const existingDistance = mapContainer.parentNode.querySelector('.distance-info');
                    if (existingDistance) {
                        existingDistance.remove();
                    }
                    distanceDisplay.classList.add('distance-info');
                    mapContainer.parentNode.appendChild(distanceDisplay);
                },
                function(error) {
                    console.log('Geolocation error:', error.message);
                }
            );
        }
    }

    // Haversine formula for distance calculation
    function getDistance(lat1, lon1, lat2, lon2) {
        const R = 6371; // Earth's radius in km
        const dLat = (lat2 - lat1) * Math.PI / 180;
        const dLon = (lon2 - lon1) * Math.PI / 180;
        const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
                  Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
                  Math.sin(dLon / 2) * Math.sin(dLon / 2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        return R * c;
    }
})();