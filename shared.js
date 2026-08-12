// Shared helpers used by windy-style-map.html, add-location.html, and
// review.html. Keeping USGS/weather/routing fetch logic in one place avoids
// pages drifting apart when one gets a bug fix and the others don't.

function parseRdb(text) {
  const lines = text.split(/\r?\n/).filter((line) => line.trim().length > 0 && !line.startsWith('#'));
  if (lines.length < 2) return [];
  const header = lines[0].split('\t');
  return lines.slice(2).map((line) => {
    const values = line.split('\t');
    return header.reduce((obj, key, index) => {
      obj[key] = values[index] === undefined ? '' : values[index];
      return obj;
    }, {});
  }).filter((site) => site.dec_lat_va && site.dec_long_va);
}

async function fetchGaugeSites() {
  const url = 'https://waterservices.usgs.gov/nwis/site/?format=rdb&stateCd=NY&siteType=ST&parameterCd=00065&siteStatus=active';
  try {
    const response = await fetch(url);
    if (!response.ok) throw new Error('Unable to fetch USGS sites');
    const text = await response.text();
    const sites = parseRdb(text);
    if (sites && sites.length) return sites;
    throw new Error('Parsed zero sites from USGS');
  } catch (err) {
    console.warn('USGS fetch failed, falling back to local JSON', err);
    try {
      const fallback = await fetch('usgs-ny-sites.json');
      if (!fallback.ok) throw new Error('Fallback JSON not found');
      return await fallback.json();
    } catch (err2) {
      console.error('Fallback failed', err2);
      return [];
    }
  }
}

async function fetchGaugeWaterHeight(siteNo) {
  const url = `https://waterservices.usgs.gov/nwis/iv/?format=json&sites=${encodeURIComponent(siteNo)}&parameterCd=00065&siteStatus=active`;
  const response = await fetch(url);
  if (!response.ok) throw new Error('Failed to fetch water height');
  const data = await response.json();
  const timeSeries = data.value?.timeSeries || [];
  if (timeSeries.length === 0) return null;
  const reading = timeSeries[0].values?.[0]?.value?.[0];
  if (!reading) return null;
  return {
    value: reading.value,
    unit: timeSeries[0].variable?.unit?.unitCode || 'ft',
    time: reading.dateTime,
  };
}

// weather.gov point lookups don't change minute to minute, so cache them
// per session instead of re-fetching every time a popup is reopened.
const weatherCache = new Map();

async function fetchWeather(lat, lon) {
  const key = `${lat.toFixed(4)},${lon.toFixed(4)}`;
  if (weatherCache.has(key)) return weatherCache.get(key);

  const pointRes = await fetch(`https://api.weather.gov/points/${lat.toFixed(4)},${lon.toFixed(4)}`);
  if (!pointRes.ok) throw new Error('Weather point lookup failed');
  const pointData = await pointRes.json();
  const forecastUrl = pointData.properties?.forecastHourly || pointData.properties?.forecast;
  if (!forecastUrl) throw new Error('No forecast available for this location');
  const forecastRes = await fetch(forecastUrl);
  if (!forecastRes.ok) throw new Error('Weather forecast fetch failed');
  const forecastData = await forecastRes.json();
  const now = forecastData.properties?.periods?.[0];
  if (!now) throw new Error('No forecast periods returned');

  const result = {
    temperature: now.temperature,
    unit: now.temperatureUnit,
    short: now.shortForecast,
    humidity: now.relativeHumidity?.value,
    windSpeed: now.windSpeed,
    windDirection: now.windDirection,
    detailed: now.detailedForecast,
  };
  weatherCache.set(key, result);
  return result;
}

const geocodeCache = new Map();

async function geocodeAddress(query) {
  const key = query.trim().toLowerCase();
  if (geocodeCache.has(key)) return geocodeCache.get(key);
  const url = `https://nominatim.openstreetmap.org/search?format=json&limit=1&q=${encodeURIComponent(query)}`;
  const res = await fetch(url, { headers: { 'Accept': 'application/json' } });
  if (!res.ok) throw new Error('Address lookup failed');
  const data = await res.json();
  if (!data.length) throw new Error('Address not found');
  const result = { lat: parseFloat(data[0].lat), lon: parseFloat(data[0].lon) };
  geocodeCache.set(key, result);
  return result;
}

const reverseGeocodeCache = new Map();

// Used to classify a point's US state when there's no other source for it
// (e.g. a Google Takeout "dropped pin" save, which only carries coordinates).
async function reverseGeocodeState(lat, lon) {
  const key = `${lat.toFixed(4)},${lon.toFixed(4)}`;
  if (reverseGeocodeCache.has(key)) return reverseGeocodeCache.get(key);
  const url = `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}&zoom=8`;
  const res = await fetch(url, { headers: { 'Accept': 'application/json' } });
  if (!res.ok) throw new Error('Reverse geocode failed');
  const data = await res.json();
  const state = data.address?.state || null;
  reverseGeocodeCache.set(key, state);
  return state;
}

const driveInfoCache = new Map();

async function fetchDriveInfo(originLat, originLon, destLat, destLon) {
  const key = `${originLat.toFixed(4)},${originLon.toFixed(4)}->${destLat.toFixed(4)},${destLon.toFixed(4)}`;
  if (driveInfoCache.has(key)) return driveInfoCache.get(key);
  const url = `https://router.project-osrm.org/route/v1/driving/${originLon},${originLat};${destLon},${destLat}?overview=false`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Routing request failed');
  const data = await res.json();
  if (data.code !== 'Ok' || !data.routes || !data.routes.length) throw new Error('No route found');
  const route = data.routes[0];
  const result = { distance: route.distance, duration: route.duration };
  driveInfoCache.set(key, result);
  return result;
}

function formatDriveDistance(meters) {
  const miles = meters / 1609.344;
  return miles >= 10 ? `${Math.round(miles)} mi` : `${miles.toFixed(1)} mi`;
}

function formatDriveDuration(seconds) {
  const mins = Math.round(seconds / 60);
  if (mins < 60) return `${mins} min`;
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return m ? `${h} hr ${m} min` : `${h} hr`;
}

function getCurrentPosition() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) return reject(new Error('Geolocation not supported'));
    navigator.geolocation.getCurrentPosition(resolve, reject, {
      timeout: 10000,
      maximumAge: 300000,
    });
  });
}
