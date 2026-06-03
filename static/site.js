function updateLiveDate() {
  const dateNode = document.getElementById("live-date");
  if (!dateNode) {
    return;
  }

  const formatter = new Intl.DateTimeFormat("en-AU", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
  dateNode.textContent = formatter.format(new Date());
}

async function hydrateToplineTemperature() {
  const tempNode = document.getElementById("live-temp");
  if (!tempNode) {
    return;
  }

  try {
    // Katoomba coordinates for a consistent Australia-wide headline temperature.
    const url = "https://api.open-meteo.com/v1/forecast?latitude=-33.715&longitude=150.311&current=temperature_2m&timezone=auto";
    const response = await fetch(url);
    const payload = await response.json();
    const current = payload.current;
    if (!current) {
      throw new Error("No weather data");
    }

    tempNode.textContent = `| ${Math.round(current.temperature_2m)}°C Katoomba`;
  } catch (error) {
    tempNode.textContent = "| Weather unavailable";
  }
}

function weatherLabel(code) {
  if (code === 0) return "Clear";
  if ([1, 2, 3].includes(code)) return "Partly cloudy";
  if ([45, 48].includes(code)) return "Fog";
  if ([51, 53, 55, 56, 57].includes(code)) return "Drizzle";
  if ([61, 63, 65, 66, 67].includes(code)) return "Rain";
  if ([71, 73, 75, 77].includes(code)) return "Snow";
  if ([80, 81, 82].includes(code)) return "Rain showers";
  if ([95, 96, 99].includes(code)) return "Thunderstorms";
  return "Local weather";
}

async function hydrateWeatherWidgets() {
  const widgets = document.querySelectorAll("[data-weather-widget]");
  for (const widget of widgets) {
    const lat = widget.getAttribute("data-lat");
    const lon = widget.getAttribute("data-lon");
    const town = widget.getAttribute("data-town") || "this town";

    if (!lat || !lon) {
      continue;
    }

    const tempNode = widget.querySelector(".weather-temp");
    const summaryNode = widget.querySelector(".weather-summary");
    const updatedNode = widget.querySelector(".weather-updated");

    try {
      const url = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current=temperature_2m,apparent_temperature,weather_code,wind_speed_10m&timezone=auto`;
      const response = await fetch(url);
      const payload = await response.json();
      const current = payload.current;
      if (!current) {
        throw new Error("No weather data");
      }

      if (tempNode) {
        tempNode.textContent = `${Math.round(current.temperature_2m)}°C`;
      }
      if (summaryNode) {
        summaryNode.textContent = `${weatherLabel(current.weather_code)} in ${town}. Feels like ${Math.round(current.apparent_temperature)}°C, wind ${Math.round(current.wind_speed_10m)} km/h.`;
      }
      if (updatedNode) {
        updatedNode.textContent = `Updated ${new Date(current.time).toLocaleTimeString("en-AU", { hour: "2-digit", minute: "2-digit" })}`;
      }
    } catch (error) {
      if (summaryNode) {
        summaryNode.textContent = `Weather feed unavailable for ${town} right now.`;
      }
      if (tempNode) {
        tempNode.textContent = "--";
      }
    }
  }
}

updateLiveDate();
hydrateToplineTemperature();
hydrateWeatherWidgets();
