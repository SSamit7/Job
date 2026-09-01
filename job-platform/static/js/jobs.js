/*
 * Working-location picker for the job create/edit form.
 * - "Use my current location" reads the browser's geolocation and fills
 *   the hidden latitude/longitude fields.
 * - The embedded map preview (an iframe, no API key required) updates
 *   live whenever the coordinates change - by clicking the button, or by
 *   the client typing new numbers in by hand.
 *
 * NOTE: this uses the keyless Google Maps "output=embed" trick, which is
 * fine for a static preview but does not support drag-to-pin. For a true
 * draggable pin picker, swap this for the Google Maps JavaScript API
 * (https://developers.google.com/maps/documentation/javascript) with a
 * real API key set in settings, and initialize a google.maps.Map +
 * google.maps.Marker instead of the iframe below.
 */
document.addEventListener("DOMContentLoaded", () => {
  const latField = document.getElementById("id_latitude");
  const lngField = document.getElementById("id_longitude");
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

  latField.addEventListener("change", updateMapPreview);
  lngField.addEventListener("change", updateMapPreview);

  // If the form is being edited and already has coordinates, show them immediately.
  updateMapPreview();

  if (geoButton) {
    geoButton.addEventListener("click", () => {
      if (!navigator.geolocation) {
        geoStatus.textContent = "Your browser doesn't support location detection - enter coordinates manually.";
        return;
      }
      geoStatus.textContent = "Detecting your current location...";
      navigator.geolocation.getCurrentPosition(
        (position) => {
          latField.value = position.coords.latitude.toFixed(6);
          lngField.value = position.coords.longitude.toFixed(6);
          updateMapPreview();
          geoStatus.textContent = "Location detected. Adjust the fields above if this isn't quite right.";
        },
        (error) => {
          geoStatus.textContent = "Couldn't get your location (" + error.message + "). Enter coordinates manually.";
        },
        { enableHighAccuracy: true, timeout: 8000 }
      );
    });
  }
});
