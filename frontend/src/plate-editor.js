// Dimensions are quantized to micrometres. A cubic micrometre is 10⁻¹⁸ m³.
const massPrecision = 18;

function thicknessMicrons(input) {
  const match = /^([0-9]+)(?:\.([0-9]+))?$/.exec(input.trim());
  if (!match) throw new Error('Enter a positive decimal thickness in mm, such as 8 or 6.125.');
  if ((match[2]?.length ?? 0) > 3) throw new Error('Use at most three decimal places (0.001 mm precision).');
  const whole = match[1].replace(/^0+(?=[0-9])/, '');
  if (whole.length > 7) throw new Error('Enter a thickness of 1,000,000 mm or less.');
  const microns = BigInt(whole) * 1000n + BigInt((match[2] ?? '').padEnd(3, '0'));
  if (microns < 1n || microns > 1_000_000_000n) {
    throw new Error('Enter a thickness from 0.001 to 1,000,000 mm.');
  }
  return microns;
}

function asDecimal(value, precision, minimum = 0) {
  const divisor = 10n ** BigInt(precision);
  const magnitude = value < 0n ? -value : value;
  const fraction = (magnitude % divisor).toString().padStart(precision, '0')
    .replace(/0+$/, '').padEnd(minimum, '0');
  return `${value < 0n ? '−' : ''}${magnitude / divisor}${fraction ? '.' + fraction : ''}`;
}

export function calculatePlateEdit(model, input) {
  const thickness = thicknessMicrons(input);
  const plate = model.components.find(part => part.kind === 'bottom');
  const microns = mm => BigInt(Math.round(mm * 1000));
  const volume = dimensions => dimensions.map(microns).reduce((a, b) => a * b, 1n);
  const density = part => BigInt(model.materials[part.material]);
  const originalPlateMass = volume(plate.size_mm) * density(plate);
  const originalAssemblyMass = model.components.reduce((total, part) =>
    total + volume(part.size_mm) * density(part), 0n);
  const revisedVolume = microns(plate.size_mm[0]) * microns(plate.size_mm[1]) * thickness;
  const revisedPlateMass = revisedVolume * density(plate);
  const massDelta = revisedPlateMass - originalPlateMass;
  const newThickness = Number(thickness) / 1000;
  const revised = {
    ...model,
    components: model.components.map(part => part === plate ? {
      ...part,
      size_mm: [...part.size_mm.slice(0, 2), newThickness],
      origin_mm: [...part.origin_mm.slice(0, 2), -newThickness],
    } : part),
  };
  const mass = value => asDecimal(value, massPrecision, 2);
  return {
    revised,
    rows: [
      ['Thickness (mm)', plate.size_mm[2], newThickness],
      ['Bottom Z (mm)', plate.origin_mm[2], -newThickness],
      ['Plate volume (m³)', asDecimal(volume(plate.size_mm), 18), asDecimal(revisedVolume, 18)],
      ['Plate mass (kg)', mass(originalPlateMass), mass(revisedPlateMass)],
      ['Assembly mass (kg)', mass(originalAssemblyMass), mass(originalAssemblyMass + massDelta)],
    ],
    delta: (massDelta > 0n ? '+' : '') + mass(massDelta),
  };
}

export function renderPlateEditor(root, model, projectHeader) {
  const plate = model.components.find(part => part.kind === 'bottom');
  root.innerHTML = `${projectHeader('Plate editor', 'Edit the baseline bottom plate and calculate the mass impact in your browser.')}
    <div class="report-grid plate-workbench">
      <section class="panel">
        <div class="panel-head"><div><h2>Bottom plate · ${plate.id}</h2><p>Z = 0 mm remains the upper face.</p></div>
          <span class="badge pass">Live calculation</span></div>
        <form class="copy-panel" id="plate-form" novalidate>
          <label for="plate-thickness">Proposed thickness (mm)</label>
          <input id="plate-thickness" name="thickness" type="text" inputmode="decimal" maxlength="24"
            value="${plate.size_mm[2]}" autocomplete="off" aria-describedby="plate-precision plate-error">
          <p id="plate-precision">0.001–1,000,000 mm, up to three decimal places.</p>
          <p id="plate-error" class="plate-error" role="alert" hidden></p>
          <div class="plate-actions">
            <button type="submit">Calculate</button>
            <button type="button" id="plate-download" disabled>Download revised model</button>
          </div>
          <p>Use the downloaded JSON with the Python CLI to regenerate engineering exports.</p>
        </form>
      </section>
      <section class="panel" aria-labelledby="plate-result-heading">
        <div class="panel-head"><div><h2 id="plate-result-heading">Mass and geometry impact</h2>
          <p>Baseline → Proposed · example steel density</p></div></div>
        <div class="copy-panel" id="plate-result" aria-live="polite"><p>Enter a thickness and select Calculate.</p></div>
      </section>
    </div>`;
  const form = root.querySelector('#plate-form');
  const input = form.querySelector('#plate-thickness');
  const error = form.querySelector('#plate-error');
  const result = root.querySelector('#plate-result');
  const download = form.querySelector('#plate-download');
  let revision;
  function clear() {
    revision = undefined;
    download.disabled = true;
    input.removeAttribute('aria-invalid');
    error.hidden = true;
    error.textContent = '';
    result.innerHTML = '<p>Enter a thickness and select Calculate.</p>';
  }
  input.addEventListener('input', clear);
  form.addEventListener('submit', event => {
    event.preventDefault();
    clear();
    let calculation;
    try {
      calculation = calculatePlateEdit(model, input.value);
    } catch (failure) {
      input.setAttribute('aria-invalid', 'true');
      error.hidden = false;
      error.textContent = failure.message;
      input.focus();
      return;
    }
    revision = calculation.revised;
    download.disabled = false;
    result.innerHTML = `<p class="plate-delta"><strong>${calculation.delta} kg</strong> assembly mass change</p>
      <div class="table-scroll"><table>
        <thead><tr><th scope="col">Quantity</th><th scope="col">Baseline</th><th scope="col">Proposed</th></tr></thead>
        <tbody>${calculation.rows.map(([name, before, after]) =>
          `<tr><th scope="row">${name}</th><td class="mono">${before}</td><td class="mono">${after}</td></tr>`
        ).join('')}</tbody>
      </table></div>`;
  });
  download.addEventListener('click', () => {
    const file = new Blob([JSON.stringify(revision, null, 2) + '\n'], { type: 'application/json' });
    const url = URL.createObjectURL(file);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'hullguard-revised-model.json';
    link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
}
