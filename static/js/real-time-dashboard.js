/**
 * Real-time Dashboard JavaScript with Live Data Updates
 */

class RealTimeDashboard {
    constructor() {
        this.updateInterval = 30000; // 30 seconds
        this.isLiveMode = false;
        this.charts = {};
        this.websocket = null;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.initializeCharts();
        this.startLiveUpdates();
        this.setupNotifications();
    }

    setupEventListeners() {
        // Live mode toggle
        const liveToggle = document.getElementById('liveToggle');
        if (liveToggle) {
            liveToggle.addEventListener('change', (e) => {
                this.toggleLiveMode(e.target.checked);
            });
        }

        // Refresh button
        const refreshBtn = document.getElementById('refreshData');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.refreshAllData();
            });
        }

        // Auto-refresh interval selector
        const intervalSelect = document.getElementById('updateInterval');
        if (intervalSelect) {
            intervalSelect.addEventListener('change', (e) => {
                this.updateInterval = parseInt(e.target.value) * 1000;
                if (this.isLiveMode) {
                    this.restartLiveUpdates();
                }
            });
        }
    }

    toggleLiveMode(enabled) {
        this.isLiveMode = enabled;
        const indicator = document.querySelector('.live-indicator');
        
        if (enabled) {
            this.startLiveUpdates();
            if (indicator) {
                indicator.style.display = 'inline-flex';
                indicator.textContent = '🔴 Live Data';
            }
            this.showNotification('Live mode enabled', 'success');
        } else {
            this.stopLiveUpdates();
            if (indicator) {
                indicator.style.display = 'none';
            }
            this.showNotification('Live mode disabled', 'info');
        }
    }

    startLiveUpdates() {
        if (this.updateTimer) {
            clearInterval(this.updateTimer);
        }

        this.updateTimer = setInterval(() => {
            if (this.isLiveMode) {
                this.fetchRealTimeData();
            }
        }, this.updateInterval);

        // Initial fetch
        this.fetchRealTimeData();
    }

    stopLiveUpdates() {
        if (this.updateTimer) {
            clearInterval(this.updateTimer);
            this.updateTimer = null;
        }
    }

    restartLiveUpdates() {
        this.stopLiveUpdates();
        if (this.isLiveMode) {
            this.startLiveUpdates();
        }
    }

    async fetchRealTimeData() {
        try {
            // Show loading indicators
            this.showLoadingIndicators();

            // Fetch multiple data sources in parallel
            const [
                vehicleData,
                weatherData,
                trafficData,
                maintenanceData,
                trackingData
            ] = await Promise.all([
                this.fetchVehicleData(),
                this.fetchWeatherData(),
                this.fetchTrafficData(),
                this.fetchMaintenanceData(),
                this.fetchTrackingData()
            ]);

            // Update UI with new data
            this.updateVehicleStats(vehicleData);
            this.updateWeatherInfo(weatherData);
            this.updateTrafficInfo(trafficData);
            this.updateMaintenanceAlerts(maintenanceData);
            this.updateLiveTracking(trackingData);
            this.updateCharts();

            // Hide loading indicators
            this.hideLoadingIndicators();

            // Update last refresh time
            this.updateLastRefreshTime();

        } catch (error) {
            console.error('Error fetching real-time data:', error);
            this.showNotification('Failed to fetch real-time data', 'error');
            this.hideLoadingIndicators();
        }
    }

    async fetchVehicleData() {
        const response = await fetch('/api/trucks');
        return await response.json();
    }

    async fetchWeatherData() {
        // Get current location or use default
        const lat = 28.7041; // Default to Delhi
        const lng = 77.1025;
        
        const response = await fetch(`/api/real_weather/${lat}/${lng}`);
        return await response.json();
    }

    async fetchTrafficData() {
        const response = await fetch('/api/traffic_status');
        return await response.json();
    }

    async fetchMaintenanceData() {
        const response = await fetch('/api/maintenance_alerts');
        return await response.json();
    }

    async fetchTrackingData() {
        const response = await fetch('/api/employee_tracking');
        return await response.json();
    }

    updateVehicleStats(data) {
        const totalVehicles = data.length;
        const activeVehicles = data.filter(v => v.status === 'In Transit').length;
        const idleVehicles = data.filter(v => v.status === 'Available').length;

        this.animateCounter('totalVehicles', totalVehicles);
        this.animateCounter('activeVehicles', activeVehicles);
        this.animateCounter('idleVehicles', idleVehicles);

        // Update efficiency percentage
        const efficiency = totalVehicles > 0 ? Math.round((activeVehicles / totalVehicles) * 100) : 0;
        this.animateCounter('fleetEfficiency', efficiency, '%');
    }

    updateWeatherInfo(data) {
        const weatherContainer = document.getElementById('weatherInfo');
        if (weatherContainer) {
            weatherContainer.innerHTML = `
                <div class="weather-card glass-card">
                    <div class="weather-icon">${this.getWeatherIcon(data.condition)}</div>
                    <div class="weather-details">
                        <h4>${data.condition}</h4>
                        <p>${data.temperature}°C</p>
                        <p>Humidity: ${data.humidity}%</p>
                        <p>Visibility: ${data.visibility}km</p>
                    </div>
                </div>
            `;
        }
    }

    updateTrafficInfo(data) {
        const trafficContainer = document.getElementById('trafficInfo');
        if (trafficContainer) {
            const trafficColor = this.getTrafficColor(data.level);
            trafficContainer.innerHTML = `
                <div class="traffic-card glass-card">
                    <div class="traffic-indicator" style="background: ${trafficColor}"></div>
                    <div class="traffic-details">
                        <h4>Traffic: ${data.level}</h4>
                        <p>Avg Delay: ${Math.round(data.delay_minutes)} min</p>
                        <p>Updated: ${new Date(data.timestamp).toLocaleTimeString()}</p>
                    </div>
                </div>
            `;
        }
    }

    updateMaintenanceAlerts(data) {
        const alertsContainer = document.getElementById('maintenanceAlerts');
        if (alertsContainer && data.alerts) {
            const criticalAlerts = data.alerts.filter(alert => alert.urgency === 'Critical');
            const warningAlerts = data.alerts.filter(alert => alert.urgency === 'Warning');

            alertsContainer.innerHTML = `
                <div class="alerts-summary">
                    <div class="alert-count critical">
                        <span class="count">${criticalAlerts.length}</span>
                        <span class="label">Critical</span>
                    </div>
                    <div class="alert-count warning">
                        <span class="count">${warningAlerts.length}</span>
                        <span class="label">Warnings</span>
                    </div>
                </div>
            `;

            // Show critical alerts as notifications
            criticalAlerts.forEach(alert => {
                this.showNotification(`Critical: ${alert.message}`, 'error', 10000);
            });
        }
    }

    updateLiveTracking(data) {
        const trackingContainer = document.getElementById('liveTracking');
        if (trackingContainer && data.length > 0) {
            const trackingHTML = data.slice(0, 5).map(track => `
                <div class="tracking-item glass-card">
                    <div class="employee-info">
                        <strong>${track.employee_id}</strong>
                        <span class="vehicle">${track.vehicle_number}</span>
                    </div>
                    <div class="status-info">
                        <span class="status ${track.trip_status.toLowerCase()}">${track.trip_status}</span>
                        <span class="time">${new Date(track.timestamp).toLocaleTimeString()}</span>
                    </div>
                </div>
            `).join('');

            trackingContainer.innerHTML = trackingHTML;
        }
    }

    initializeCharts() {
        // Initialize Chart.js charts for real-time data visualization
        this.initCarbonTrendChart();
        this.initFuelConsumptionChart();
        this.initEfficiencyChart();
    }

    initCarbonTrendChart() {
        const ctx = document.getElementById('carbonTrendChart');
        if (ctx) {
            this.charts.carbonTrend = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'CO₂ Emissions (kg)',
                        data: [],
                        borderColor: '#11998e',
                        backgroundColor: 'rgba(17, 153, 142, 0.1)',
                        tension: 0.4,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: {
                                color: 'rgba(255, 255, 255, 0.1)'
                            }
                        },
                        x: {
                            grid: {
                                color: 'rgba(255, 255, 255, 0.1)'
                            }
                        }
                    },
                    animation: {
                        duration: 1000,
                        easing: 'easeInOutQuart'
                    }
                }
            });
        }
    }

    initFuelConsumptionChart() {
        const ctx = document.getElementById('fuelConsumptionChart');
        if (ctx) {
            this.charts.fuelConsumption = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: ['Diesel', 'Petrol', 'Electric'],
                    datasets: [{
                        data: [70, 25, 5],
                        backgroundColor: [
                            '#667eea',
                            '#764ba2',
                            '#11998e'
                        ],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            position: 'bottom'
                        }
                    },
                    animation: {
                        animateRotate: true,
                        duration: 1500
                    }
                }
            });
        }
    }

    initEfficiencyChart() {
        const ctx = document.getElementById('efficiencyChart');
        if (ctx) {
            this.charts.efficiency = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                    datasets: [{
                        label: 'Efficiency %',
                        data: [85, 92, 78, 95, 88, 82, 90],
                        backgroundColor: 'rgba(102, 126, 234, 0.8)',
                        borderColor: '#667eea',
                        borderWidth: 2,
                        borderRadius: 8
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100,
                            grid: {
                                color: 'rgba(255, 255, 255, 0.1)'
                            }
                        },
                        x: {
                            grid: {
                                display: false
                            }
                        }
                    },
                    animation: {
                        duration: 1200,
                        easing: 'easeOutBounce'
                    }
                }
            });
        }
    }

    updateCharts() {
        // Update charts with new data
        if (this.charts.carbonTrend) {
            this.updateCarbonTrendChart();
        }
        if (this.charts.fuelConsumption) {
            this.updateFuelConsumptionChart();
        }
        if (this.charts.efficiency) {
            this.updateEfficiencyChart();
        }
    }

    updateCarbonTrendChart() {
        const chart = this.charts.carbonTrend;
        const now = new Date();
        const timeLabel = now.toLocaleTimeString();
        
        // Add new data point
        chart.data.labels.push(timeLabel);
        chart.data.datasets[0].data.push(Math.random() * 100 + 50);
        
        // Keep only last 10 data points
        if (chart.data.labels.length > 10) {
            chart.data.labels.shift();
            chart.data.datasets[0].data.shift();
        }
        
        chart.update('none');
    }

    updateFuelConsumptionChart() {
        const chart = this.charts.fuelConsumption;
        // Simulate changing fuel consumption data
        const newData = [
            Math.random() * 30 + 60,
            Math.random() * 20 + 20,
            Math.random() * 10 + 5
        ];
        chart.data.datasets[0].data = newData;
        chart.update();
    }

    updateEfficiencyChart() {
        const chart = this.charts.efficiency;
        // Update with new efficiency data
        chart.data.datasets[0].data = chart.data.datasets[0].data.map(() => 
            Math.random() * 20 + 75
        );
        chart.update();
    }

    animateCounter(elementId, targetValue, suffix = '') {
        const element = document.getElementById(elementId);
        if (!element) return;

        const startValue = parseInt(element.textContent) || 0;
        const duration = 1000;
        const startTime = performance.now();

        const animate = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            // Easing function
            const easeOutQuart = 1 - Math.pow(1 - progress, 4);
            const currentValue = Math.round(startValue + (targetValue - startValue) * easeOutQuart);
            
            element.textContent = currentValue + suffix;
            
            if (progress < 1) {
                requestAnimationFrame(animate);
            }
        };

        requestAnimationFrame(animate);
    }

    showLoadingIndicators() {
        const indicators = document.querySelectorAll('.loading-indicator');
        indicators.forEach(indicator => {
            indicator.style.display = 'block';
        });
    }

    hideLoadingIndicators() {
        const indicators = document.querySelectorAll('.loading-indicator');
        indicators.forEach(indicator => {
            indicator.style.display = 'none';
        });
    }

    updateLastRefreshTime() {
        const timeElement = document.getElementById('lastRefreshTime');
        if (timeElement) {
            timeElement.textContent = `Last updated: ${new Date().toLocaleTimeString()}`;
        }
    }

    getWeatherIcon(condition) {
        const icons = {
            'Clear': '☀️',
            'Cloudy': '☁️',
            'Rainy': '🌧️',
            'Foggy': '🌫️',
            'Snow': '❄️'
        };
        return icons[condition] || '🌤️';
    }

    getTrafficColor(level) {
        const colors = {
            'Low': '#11998e',
            'Medium': '#f093fb',
            'High': '#f5576c'
        };
        return colors[level] || '#667eea';
    }

    setupNotifications() {
        // Request notification permission
        if ('Notification' in window && Notification.permission === 'default') {
            Notification.requestPermission();
        }
    }

    showNotification(message, type = 'info', duration = 5000) {
        // Create toast notification
        const toast = document.createElement('div');
        toast.className = `toast-enhanced toast-${type}`;
        toast.innerHTML = `
            <div class="toast-content">
                <span class="toast-icon">${this.getNotificationIcon(type)}</span>
                <span class="toast-message">${message}</span>
                <button class="toast-close" onclick="this.parentElement.parentElement.remove()">×</button>
            </div>
        `;

        document.body.appendChild(toast);

        // Auto remove after duration
        setTimeout(() => {
            if (toast.parentElement) {
                toast.remove();
            }
        }, duration);

        // Browser notification for critical alerts
        if (type === 'error' && 'Notification' in window && Notification.permission === 'granted') {
            new Notification('Critical Alert', {
                body: message,
                icon: '/static/images/alert-icon.png'
            });
        }
    }

    getNotificationIcon(type) {
        const icons = {
            'success': '✅',
            'error': '❌',
            'warning': '⚠️',
            'info': 'ℹ️'
        };
        return icons[type] || 'ℹ️';
    }

    refreshAllData() {
        this.showNotification('Refreshing all data...', 'info');
        this.fetchRealTimeData();
    }

    destroy() {
        this.stopLiveUpdates();
        if (this.websocket) {
            this.websocket.close();
        }
        
        // Destroy charts
        Object.values(this.charts).forEach(chart => {
            if (chart) chart.destroy();
        });
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.realTimeDashboard = new RealTimeDashboard();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.realTimeDashboard) {
        window.realTimeDashboard.destroy();
    }
});