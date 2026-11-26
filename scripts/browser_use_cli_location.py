"""Recover a city field backed by Google Places on an attached application tab."""

from browser_use_cli_form import evaluate


CITY_INPUTS = r"""
({url, citySelector, latitudeName, longitudeName}) => {
  if (location.href !== url) return null;
  const candidates = document.querySelectorAll(citySelector);
  if (candidates.length !== 1) return null;
  const [city] = candidates;
  if (!(city instanceof HTMLInputElement) || !city.form || !city.name ||
      !["hidden", "text", "search"].includes(city.type)) return null;
  if (city.form.elements.namedItem(city.name) !== city) return null;
  const coordinateNames = [latitudeName, longitudeName];
  const coordinates = coordinateNames.map(name => city.form.elements.namedItem(name));
  if (coordinates.some((input, index) => input?.name !== coordinateNames[index])) return null;
  const inputs = [city, ...coordinates];
  if (new Set(inputs).size !== inputs.length) return null;
  return inputs.every(input => input instanceof HTMLInputElement && !input.matches(":disabled") && !input.readOnly)
    ? inputs : null;
}
"""

READ_CITY = f"""
scope => {{
  const inputs = ({CITY_INPUTS})(scope);
  return inputs?.map(input => input.value) ?? null;
}}
"""

LOOK_UP_CITY = r"""
async (url, query, choice) => {
  if (location.href !== url) {
    return {status: "blocked", detail: "The application tab changed before the city lookup."};
  }
  const places = globalThis.google?.maps?.places;
  if (!places?.AutocompleteService || !places?.PlacesService) {
    return {status: "blocked", detail: "Google Places is unavailable on this form."};
  }
  const normalize = label => label.trim().toLowerCase().replace(/\s*,\s*/g, ",");
  try {
    const {predictions} = await new places.AutocompleteService()
      .getPlacePredictions({input: query, types: ["(cities)"]});
    if (!predictions.length) {
      return {status: "blocked", detail: "The lookup returned no cities for this query."};
    }
    const matches = predictions.filter(place => normalize(place.description) === normalize(choice));
    if (matches.length !== 1) {
      return {status: "choose_city", choices: predictions.map(place => place.description)};
    }
    const service = new places.PlacesService(document.createElement("div"));
    const place = await new Promise(resolve => service.getDetails(
      {placeId: matches[0].place_id, fields: ["formatted_address", "geometry"]},
      (result, status) => resolve(status === "OK" ? result : null)
    ));
    const latitude = place?.geometry?.location?.lat();
    const longitude = place?.geometry?.location?.lng();
    if (!place?.formatted_address || !Number.isFinite(latitude) || Math.abs(latitude) > 90 ||
        !Number.isFinite(longitude) || Math.abs(longitude) > 180) {
      return {status: "blocked", detail: "The selected city did not return usable coordinates."};
    }
    return {status: "resolved", values: [place.formatted_address, String(latitude), String(longitude)]};
  } catch {
    return {status: "blocked", detail: "The city lookup did not complete."};
  }
}
"""

WRITE_CITY = f"""
async (scope, before, values) => {{
  const findInputs = ({CITY_INPUTS});
  const inputs = findInputs(scope);
  if (!inputs || inputs.some((input, index) => input.value !== before[index])) {{
    return {{status: "blocked", detail: "The form changed during the city lookup."}};
  }}
  const form = inputs[0].form;
  const names = inputs.map(input => input.name);
  const types = inputs.map(input => input.type);
  const setValue = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set;
  function write(fields, values, types) {{
    try {{
      fields.forEach((field, index) => {{
        // Let the form's text input handlers see changes to the hidden fields.
        field.type = "text";
        setValue.call(field, values[index]);
      }});
      for (const field of fields) {{
        field.dispatchEvent(new Event("input", {{bubbles: true}}));
        field.dispatchEvent(new Event("change", {{bubbles: true}}));
      }}
    }} finally {{
      fields.forEach((field, index) => {{
        const value = field.value;
        field.type = types[index];
        // A hidden input can keep its old value attribute when the text value is empty.
        if (field.type === "hidden") setValue.call(field, value);
      }});
    }}
  }}

  const cityType = types[0] === "hidden" ? "text" : types[0];
  write(inputs, values, [cityType, ...types.slice(1)]);
  await Promise.resolve();
  const current = names.map(name => form.elements.namedItem(name));
  if (location.href === scope.url && form.isConnected &&
      current.every((input, index) => input instanceof HTMLInputElement && input.name === names[index])) {{
    const data = new FormData(form);
    if (current.every((input, index) => data.get(input.name) === values[index])) {{
      return {{status: "filled", city: values[0]}};
    }}
    if (current.every((input, index) => [before[index], values[index]].includes(input.value))) {{
      write(current, before, types);
    }}
  }}
  return {{status: "blocked", detail: "The form did not retain the selected city and coordinates."}};
}}
"""


def repair_city(cdp, session_id, url, query, *, city_selector='input[name="location"]',
                latitude_name="latitude", longitude_name="longitude", choice=None):
    """Fill observed city and coordinate fields with a verified Places result."""
    scope = {"url": url, "citySelector": city_selector,
             "latitudeName": latitude_name, "longitudeName": longitude_name}
    before = evaluate(cdp, session_id, READ_CITY, scope)
    if before is None:
        return {"status": "blocked", "detail": "Could not match the city and coordinate fields on this form."}
    city, latitude, longitude = before
    try:
        has_coordinates = -90 <= float(latitude) <= 90 and -180 <= float(longitude) <= 180
    except ValueError:
        has_coordinates = False
    if city.strip() and has_coordinates:
        return {"status": "already_filled", "city": city}

    lookup = evaluate(cdp, session_id, LOOK_UP_CITY, url, query, choice or query)
    if lookup["status"] != "resolved":
        return lookup
    return evaluate(cdp, session_id, WRITE_CITY, scope, before, lookup["values"])
