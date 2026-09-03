/*
 * Working-location picker for the job create/edit form.
 * - "Use my current location" reads the browser's geolocation, fills the
 *   latitude/longitude fields, THEN reverse-geocodes those coordinates
 *   (via OpenStreetMap's free Nominatim API - no key needed) to also fill
 *   in the Location and Address text fields automatically.
 * - The embedded map preview (an iframe, no API key required) updates
 *   live whenever the coordinates change - by clicking the button, or by
 *   the client typing new numbers in by hand.
 * - Everything it fills in stays editable - if the auto-detected address
 *   isn't quite right, just type over it.
 *
 * NOTE: this uses the keyless Google Maps "output=embed" trick for the map
 * preview, which is fine for a static preview but does not support
 * drag-to-pin. For a true draggable pin picker, swap this for the Google
 * Maps JavaScript API with a real API key, and initialize a
 * google.maps.Map + google.maps.Marker instead of the iframe below.
 */
document.addEventListener("DOMContentLoaded", () => {
  const latField = document.getElementById("id_latitude");
  const lngField = document.getElementById("id_longitude");
  const locationField = document.getElementById("id_location");
  const addressField = document.getElementById("id_address");
  const mapFrame = document.getElementById("location-map");
  const geoButton = document.getElementById("use-current-location");
  const geoStatus = document.getElementById("geo-status");

  if (!latField || !lngField || !mapFrame) return;

  function updateMapPreview() {
    const lat = parseFloat(latField.value);
    const lng = parseFloat(lngField.value);
    if (Number.isFinite(lat) && Number.isFinite(lng)) {
      mapFrame.src = `https://maps.google.com/maps?q=${lat},${lng}&z=15&output=embed`;
    }
  }

  async function reverseGeocode(lat, lng) {
    const url = `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${lat}&lon=${lng}&zoom=16&addressdetails=1`;
    const response = await fetch(url, { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error("Reverse geocoding request failed");
    return response.json();
  }

  latField.addEventListener("change", updateMapPreview);
  lngField.addEventListener("change", updateMapPreview);

  // If the form is being edited and already has coordinates, show them immediately.
  updateMapPreview();

  if (geoButton) {
    geoButton.addEventListener("click", () => {
      if (!navigator.geolocation) {
        geoStatus.textContent = "Your browser doesn't support location detection - enter the fields manually.";
        return;
      }
      geoStatus.textContent = "Detecting your current location...";
      navigator.geolocation.getCurrentPosition(
        async (position) => {
          const lat = position.coords.latitude;
          const lng = position.coords.longitude;
          latField.value = lat.toFixed(6);
          lngField.value = lng.toFixed(6);
          updateMapPreview();
          geoStatus.textContent = "Location detected - looking up the address...";

          try {
            const data = await reverseGeocode(lat, lng);
            const addr = data.address || {};

            if (locationField) {
              const cityLike = addr.city || addr.town || addr.village || addr.municipality || addr.county || "";
              locationField.value = [cityLike, addr.country].filter(Boolean).join(", ");
            }
            if (addressField) {
              const streetLike = [addr.house_number, addr.road].filter(Boolean).join(" ");
              const neighbourhood = addr.suburb || addr.neighbourhood || "";
              addressField.value = [streetLike, neighbourhood].filter(Boolean).join(", ") || data.display_name || "";
            }

            geoStatus.textContent = "Location detected and address filled in. Adjust any field above if this isn't quite right.";
          } catch (err) {
            geoStatus.textContent =
              "Got your coordinates, but couldn't look up the address automatically - please fill in Location/Address by hand.";
          }
        },
        (error) => {
          geoStatus.textContent = "Couldn't get your location (" + error.message + "). Enter the fields manually.";
        },
        { enableHighAccuracy: true, timeout: 8000 }
      );
    });
  }
});
