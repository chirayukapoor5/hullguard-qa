import '@fontsource/barlow/latin-400.css';
import '@fontsource/barlow/latin-500.css';
import '@fontsource/barlow/latin-600.css';
import '@fontsource/barlow/latin-700.css';
import '@fontsource/ibm-plex-mono/latin-400.css';
import './style.css';
import { mountViewer } from './viewer.js';

const root = document.querySelector('main');
const dataRoot = `${import.meta.env.BASE_URL}data/`;
const routes = ['structure', 'revisions', 'checks', 'faults', 'report'];
const kinds = { bottom: 'Bottom plate', side: 'Side plate', bulkhead: 'Transverse bulkhead', stiffener: 'Longitudinal stiffener' };
const files = {
  'model.obj': '3D mesh (OBJ)', 'manifest.json': 'Manifest (JSON)', 'bom.csv': 'BOM (CSV)',
  'drawing.svg': 'Technical plan (SVG)', 'validation.json': 'Validation (JSON)',
  'report.html': 'Engineering report (HTML)', 'comparison.json': 'Comparison (JSON)',
  'model.json': 'Source model (JSON)',
};
const escape = value => String(value).replace(/[&<>"']/g, symbol => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
})[symbol]);
const number = new Intl.NumberFormat('en-US', { maximumFractionDigits: 3 });
const mass = new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 3 });
const delta = new Intl.NumberFormat('en-US', { signDisplay: 'exceptZero', minimumFractionDigits: 2, maximumFractionDigits: 3 });
const vector = values => values.map(value => number.format(value)).join(' × ');
const revisionLabel = row => row.id === 'baseline' ? 'Baseline' : row.id === 'thickness_changed' ? 'Plate thickness' : 'Stiffener layout';
const badge = (label, tone) => `<span class="badge ${tone}">${escape(label)}</span>`;
const evidenceLink = (row, file, label = files[file]) =>
  `<a href="${dataRoot}${escape(row.directory)}/${file}">${escape(label)}</a>`;

async function fetchFile(path, reading = 'json') {
  const response = await fetch(`${dataRoot}${path}`);
  if (!response.ok) throw new Error(`${path} returned HTTP ${response.status}`);
  return response[reading]();
}

let catalog;
let revisionId = 'baseline';
let comparisonId = 'thickness_changed';
let faultId = 'stale_bom';
let renderGeneration = 0;
let activeViewer;
const cache = new Map();

function getRevision(id) {
  if (!cache.has(id)) {
    const row = catalog.revisions.find(entry => entry.id === id);
    const read = file => fetchFile(`${row.directory}/${file}`);
    const promise = Promise.all([
      read('manifest.json'),
      id === 'baseline' ? null : read('comparison.json'),
    ]).then(([manifest, comparison]) => ({ row, manifest, comparison }));
    cache.set(id, promise);
    promise.catch(() => cache.delete(id));
  }
  return cache.get(id);
}

function projectHeader(title, description, action = '') {
  return `<div class="page-heading"><div><h1>${title}</h1><p>${description}</p></div>${action}</div>`;
}

function picker(id, label, entries, selected, renderLabel = entry => entry.title) {
  return `<div class="picker"><label for="${id}">${label}</label>
    <select id="${id}">${entries.map(row =>
      `<option value="${row.id}" ${row.id === selected ? 'selected' : ''}>${escape(renderLabel(row))}</option>`
    ).join('')}</select></div>`;
}

function statusStrip(manifest, status, options = {}) {
  const { change, count = manifest.components.length } = options;
  return `<div class="metrics">
    <div><span>Assembly mass</span><strong>${mass.format(manifest.assembly_mass_kg)} <small>kg</small></strong></div>
    <div><span>${change === undefined ? 'Components' : 'Assembly mass change'}</span>
      <strong>${change === undefined ? count : `${delta.format(change)} <small>kg</small>`}</strong></div>
    <div><span>Export consistency</span><strong class="result ${status.toLowerCase()}">${status}</strong></div>
    <div><span>Source revision</span><strong class="revision-hash" title="${manifest.revision}">${manifest.revision.slice(0, 12)}</strong></div>
  </div>`;
}

function partTable(components, selectable = false) {
  return `<div class="table-scroll"><table><thead><tr>
    <th scope="col">Component</th><th scope="col">Type</th><th scope="col">XYZ dimensions (mm)</th>
    <th scope="col">Thickness (mm)</th><th scope="col">Mass (kg)</th></tr></thead><tbody>
    ${components.map(p => `<tr data-row="${p.id}"><th scope="row">
      ${selectable ? `<button type="button" class="text-button mono" data-pick="${p.id}">${p.id}</button>` : p.id}</th>
      <td>${kinds[p.kind]}</td><td class="mono">${vector(p.size_mm)}</td>
      <td class="mono">${number.format(p.thickness_mm)}</td><td class="mono">${mass.format(p.mass_kg)}</td></tr>`).join('')}
    </tbody></table></div>`;
}

function meshPanel(title, row, compact = false) {
  return `<section class="panel mesh-panel"><div class="panel-head"><div>
    <h2>${title}</h2><p>Open structural bay · Wavefront OBJ</p></div>
    ${badge('Millimetres', 'neutral')}</div>
    <div class="viewport ${compact ? 'compact' : ''}">
      <div class="mesh-host"></div><p class="mesh-status" role="status">Loading OBJ…</p>
      <div class="mesh-controls" aria-label="Camera controls">
        <button type="button" data-camera="zoomIn" aria-label="Zoom in">+</button>
        <button type="button" data-camera="zoomOut" aria-label="Zoom out">−</button>
        <button type="button" data-camera="reset">Reset view</button>
      </div>
      <div class="mesh-axes" aria-hidden="true"><span>X</span> Longitudinal <span>Y</span> Transverse <span>Z</span> Vertical</div>
    </div><div class="panel-foot"><span>Drag to rotate · Scroll to zoom · Select a part to inspect</span>
      ${evidenceLink(row, 'model.obj', 'Open OBJ')}</div></section>`;
}

async function attachMesh(row, manifest, select, generation, changed = []) {
  const host = root.querySelector('.mesh-host');
  const status = root.querySelector('.mesh-status');
  try {
    const content = await fetchFile(`${row.directory}/model.obj`, 'text');
    if (generation !== renderGeneration) return;
    activeViewer = mountViewer(host, content, manifest.components, select, changed);
    status.textContent = `${manifest.components.length} mesh objects`;
    const actions = { zoomIn: () => activeViewer.zoom(0.83), zoomOut: () => activeViewer.zoom(1.2), reset: () => activeViewer.reset() };
    for (const button of root.querySelectorAll('[data-camera]')) {
      button.addEventListener('click', actions[button.dataset.camera]);
    }
    return activeViewer;
  } catch {
    if (generation === renderGeneration) {
      status.textContent = '3D preview unavailable. Open the OBJ or use the component inventory.';
      for (const button of root.querySelectorAll('[data-camera]')) button.disabled = true;
    }
  }
}

function detail(part) {
  return `<div class="part-title"><span class="part-symbol ${part.kind}" aria-hidden="true"></span><div>
    <strong class="mono">${part.id}</strong><span>${kinds[part.kind]}</span></div></div>
    <dl class="properties">
      <div><dt>Nominal dimensions (XYZ)</dt><dd>${vector(part.size_mm)} mm</dd></div>
      <div><dt>Position (XYZ)</dt><dd>${vector(part.origin_mm)} mm</dd></div>
      <div><dt>Thickness</dt><dd>${number.format(part.thickness_mm)} mm</dd></div>
      <div><dt>Material</dt><dd>Steel · example</dd></div>
      <div><dt>Density</dt><dd>${number.format(part.density_kg_m3)} kg/m³</dd></div>
      <div><dt>Calculated mass</dt><dd>${mass.format(part.mass_kg)} kg</dd></div>
    </dl>`;
}

async function structure(generation) {
  const { row, manifest } = await getRevision(revisionId);
  if (generation !== renderGeneration) return;
  const options = manifest.components.map(p => ({ id: p.id, title: `${p.id} · ${kinds[p.kind]}` }));
  const first = manifest.components.find(p => p.kind === 'bottom').id;
  root.innerHTML = `${projectHeader('Structure explorer', 'Inspect the exported geometry and the properties behind each component.',
    picker('revision', 'Model revision', catalog.revisions, revisionId, revisionLabel))}
    ${statusStrip(manifest, row.validation.status)}
    <div class="workbench">
      ${meshPanel('Structural model', row)}
      <section class="panel inspector"><div class="panel-head"><div><h2>Component inspector</h2>
        <p>Properties from the verified manifest</p></div></div><div class="inspector-body">
        ${picker('component', 'Component', options, first)}
        <div id="part-detail" aria-live="polite"></div></div></section>
    </div>
    <section class="panel inventory"><div class="panel-head"><div><h2>Component inventory</h2>
      <p>Mass and dimensions by structural element</p></div>${evidenceLink(row, 'bom.csv', 'Open BOM')}</div>
      ${partTable(manifest.components, true)}
    </section>`;
  let selected = first;
  function select(id) {
    const part = manifest.components.find(entry => entry.id === id);
    if (!part) return;
    selected = id;
    root.querySelector('#component').value = id;
    root.querySelector('#part-detail').innerHTML = detail(part);
    for (const tableRow of root.querySelectorAll('[data-row]')) tableRow.classList.toggle('selected', tableRow.dataset.row === id);
    activeViewer?.select(id);
  }
  select(first);
  root.querySelector('#revision').addEventListener('change', event => {
    revisionId = event.target.value;
    render();
  });
  root.querySelector('#component').addEventListener('change', event => select(event.target.value));
  for (const button of root.querySelectorAll('[data-pick]')) button.addEventListener('click', () => select(button.dataset.pick));
  const viewer = await attachMesh(row, manifest, select, generation);
  viewer?.select(selected);
}

function partDelta(comparison) {
  const rows = [
    ...comparison.modified.map(change => ({ ...change, type: 'Modified' })),
    ...comparison.added.map(part => ({ id: part.id, after: part, delta_mass_kg: part.mass_kg, type: 'Added' })),
    ...comparison.removed.map(part => ({ id: part.id, before: part, delta_mass_kg: -part.mass_kg, type: 'Removed' })),
  ];
  const display = (part, key, formatter) => part ? formatter.format(part[key]) : '—';
  return `<div class="table-scroll"><table><thead><tr>
    <th scope="col">Component</th><th scope="col">Change</th>
    <th scope="col">Thickness (mm)</th><th scope="col">Mass (kg)</th><th scope="col">Δ mass (kg)</th>
  </tr></thead><tbody>${rows.map(row => `<tr><th scope="row" class="mono">${row.id}</th>
    <td>${badge(row.type, 'neutral')}</td>
    <td class="mono">${display(row.before, 'thickness_mm', number)} → ${display(row.after, 'thickness_mm', number)}</td>
    <td class="mono">${display(row.before, 'mass_kg', mass)} → ${display(row.after, 'mass_kg', mass)}</td>
    <td class="mono">${delta.format(row.delta_mass_kg)}</td></tr>`).join('')}</tbody></table></div>`;
}

async function revisions(generation) {
  const { row, manifest, comparison } = await getRevision(comparisonId);
  if (generation !== renderGeneration) return;
  const changed = [...comparison.modified, ...comparison.added].map(part => part.id);
  root.innerHTML = `${projectHeader('Revision comparison', 'Compare the baseline with an edited model and inspect its downstream impact.',
    picker('comparison', 'Compare to baseline', catalog.revisions.filter(r => r.id !== 'baseline'), comparisonId, revisionLabel))}
    ${statusStrip(manifest, row.validation.status, { change: comparison.delta_mass_kg })}
    <div class="workbench"><div>
      ${meshPanel('Revised structure', row, true)}</div>
      <section class="panel"><div class="panel-head"><div><h2>Revision impact</h2><p>Baseline → ${revisionLabel(row)}</p></div></div>
        <div class="copy-panel"><dl class="properties">
          <div><dt>Baseline assembly</dt><dd>${mass.format(comparison.before_mass_kg)} kg</dd></div>
          <div><dt>Revised assembly</dt><dd>${mass.format(comparison.after_mass_kg)} kg</dd></div>
          <div><dt>Components changed</dt><dd>${comparison.modified.length} modified · ${comparison.added.length} added · ${comparison.removed.length} removed</dd></div>
        </dl><p>Amber geometry marks modified or added parts. Removed parts appear in the change table.</p>
        <p id="revision-pick" role="status">Select a part on the model to identify it.</p>
        ${evidenceLink(row, 'comparison.json', 'Open position and dimension deltas')}</div></section>
    </div>
    <section class="panel inventory"><div class="panel-head"><div><h2>Changed components</h2>
      <p>Baseline value → revised value</p></div></div>${partDelta(comparison)}</section>`;
  root.querySelector('#comparison').addEventListener('change', event => {
    comparisonId = event.target.value;
    render();
  });
  await attachMesh(row, manifest, id => {
    activeViewer?.select(id);
    root.querySelector('#revision-pick').textContent = `Selected ${id} · ${changed.includes(id) ? 'changed' : 'unchanged'}`;
  }, generation, changed);
}

function findingTable(validation) {
  if (!validation.findings.length) return '<p>All checked artifacts reconciled to the source model.</p>';
  const show = value => escape(typeof value === 'string' ? value : JSON.stringify(value));
  return `<div class="table-scroll"><table class="finding-table"><thead><tr><th scope="col">Finding</th>
    <th scope="col">Component</th><th scope="col">Expected</th><th scope="col">Actual</th></tr></thead><tbody>
    ${validation.findings.map(f => `<tr><th scope="row" class="mono">${escape(f.code)}</th>
      <td>${escape(f.component || 'Bundle')}</td><td class="break">${show(f.expected)}</td>
      <td class="break">${show(f.actual)}</td></tr>`).join('')}</tbody></table></div>`;
}

function goToFault(id) {
  faultId = id;
  location.hash = 'faults';
}

function checks() {
  const passed = catalog.revisions.filter(row => row.validation.status === 'PASS').length;
  const matched = catalog.faults.filter(row => row.matched && row.validation.status === 'FAIL').length;
  root.innerHTML = `${projectHeader('QA dashboard', 'Recorded results from the Python validator for verified revisions and controlled faults.')}
    <div class="metrics"><div><span>Healthy revisions</span><strong>${passed} / ${catalog.revisions.length}</strong></div>
      <div><span>Expected fault detections</span><strong>${matched} / ${catalog.faults.length}</strong></div>
      <div><span>Evidence mode</span><strong class="revision-hash">Precomputed</strong></div></div>
    <section class="panel"><div class="panel-head"><h2>Automated scenario results</h2></div>
      <div class="table-scroll"><table><thead><tr>
        <th scope="col">Scenario</th><th scope="col">Validator status</th><th scope="col">Expected</th>
        <th scope="col">Actual</th><th scope="col">Evidence</th></tr></thead><tbody>
      ${catalog.revisions.map(row => `<tr><th scope="row">${escape(row.title)}</th>
        <td>${badge(row.validation.status, row.validation.status.toLowerCase())}</td><td>4 exports reconcile</td>
        <td>${row.validation.findings.length} findings</td><td>${evidenceLink(row, 'validation.json')}</td></tr>`).join('')}
      ${catalog.faults.map(row => `<tr><th scope="row">${escape(row.title)}</th>
        <td>${badge(row.validation.status, row.validation.status.toLowerCase())}</td><td class="mono">${escape(row.expected_detector)}</td>
        <td>${row.matched ? 'Expected finding observed' : 'Expected finding absent'}</td>
        <td><button type="button" class="text-button" data-fault="${row.id}">Reproduce ${escape(row.title)}</button></td></tr>`).join('')}
      </tbody></table></div>
    </section>`;
  for (const button of root.querySelectorAll('[data-fault]')) button.addEventListener('click', () => goToFault(button.dataset.fault));
}

function faults() {
  const row = catalog.faults.find(entry => entry.id === faultId);
  root.innerHTML = `${projectHeader('Fault injection', 'Inspect deliberate defects in synthetic exports using precomputed validator results.',
    picker('fault', 'Synthetic scenario', catalog.faults, faultId))}
    <div class="metrics"><div><span>Validator status</span><strong class="result ${row.validation.status.toLowerCase()}">${row.validation.status}</strong></div>
      <div><span>Expected detector</span><strong class="revision-hash">${escape(row.expected_detector)}</strong></div>
      <div><span>Acceptance outcome</span><strong class="revision-hash">${row.matched ? 'Expected fault detected' : 'Detector mismatch'}</strong></div></div>
    <section class="panel"><div class="panel-head"><div><h2>${escape(row.title)}</h2><p>${escape(row.description)}</p></div>
      ${badge('Controlled fault', 'neutral')}</div>
      ${findingTable(row.validation)}
      <div class="copy-panel"><h3>Reproduce locally</h3><p>Generate all evidence from the repository root, then run the validator against this case.</p>
      <pre><code>python -m hullguard demo
${escape(row.reproduce)}</code></pre>
      <div class="link-list">${evidenceLink(row, row.artifact, 'Open faulty artifact')}${evidenceLink(row, 'validation.json')}</div>
      </div></section>`;
  root.querySelector('#fault').addEventListener('change', event => {
    faultId = event.target.value;
    faults();
    root.querySelector('#fault').focus();
  });
}

async function report(generation) {
  const { row, manifest, comparison } = await getRevision(revisionId);
  if (generation !== renderGeneration) return;
  root.innerHTML = `${projectHeader('Engineering report', 'Review the source revision, component schedule, validation, and export evidence.',
    picker('report-revision', 'Report revision', catalog.revisions, revisionId, revisionLabel))}
    ${statusStrip(manifest, row.validation.status, comparison ? { change: comparison.delta_mass_kg } : {})}
    <div class="report-grid">
      <section class="panel"><div class="panel-head"><h2>Export consistency</h2></div>
        <div class="copy-panel"><p>${row.validation.checked.length} exports checked against the canonical model.</p>
          ${findingTable(row.validation)}
          <p class="break mono">${manifest.revision}</p>
          ${comparison ? `<p>${comparison.modified.length} modified, ${comparison.added.length} added and ${comparison.removed.length} removed since baseline.</p>
            ${evidenceLink(row, 'comparison.json')}` : '<p>This revision is the comparison baseline.</p>'}
        </div></section>
      <section class="panel"><div class="panel-head"><h2>Evidence files</h2></div>
        <div class="copy-panel link-list vertical">${['report.html', 'drawing.svg', 'bom.csv', 'model.obj', 'manifest.json', 'validation.json', 'model.json']
          .map(file => evidenceLink(row, file)).join('')}</div></section>
    </div>
    <section class="panel inventory"><div class="panel-head"><h2>Component inventory</h2></div>${partTable(manifest.components)}</section>
    <section class="panel inventory"><div class="panel-head"><h2>Model scope</h2></div>
      <div class="copy-panel"><p>Synthetic rectangular solids, one example steel density, and schematic plan dimensions.
        Structural strength, class approval, and production drawings are outside scope.</p></div></section>`;
  root.querySelector('#report-revision').addEventListener('change', event => {
    revisionId = event.target.value;
    render();
  });
}

const views = { structure, revisions, checks, faults, report };

async function render() {
  if (!catalog) return;
  const generation = ++renderGeneration;
  activeViewer?.dispose();
  activeViewer = undefined;
  const requested = location.hash.slice(1);
  const route = routes.includes(requested) ? requested : 'structure';
  for (const link of document.querySelectorAll('.navigation a')) {
    if (link.hash === `#${route}`) link.setAttribute('aria-current', 'page');
    else link.removeAttribute('aria-current');
  }
  try {
    await views[route](generation);
  } catch (error) {
    if (generation === renderGeneration) {
      root.innerHTML = `<h1>Evidence unavailable</h1><p role="alert">${escape(error.message)}</p>`;
    }
  }
}

window.addEventListener('hashchange', () => {
  if (location.hash === '#main-content') return;
  window.scrollTo(0, 0);
  render();
});
try {
  catalog = await fetchFile('index.json');
  await render();
} catch (error) {
  root.innerHTML = `<h1>Evidence unavailable</h1><p role="alert">Run the Python demo generator before building the frontend. ${escape(error.message)}</p>`;
}
