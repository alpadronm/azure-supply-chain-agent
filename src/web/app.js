const summaryEls = {
  tiendas: document.getElementById('tiendasValue'),
  productos: document.getElementById('productosValue'),
  inventarioTiendas: document.getElementById('inventarioTiendasValue'),
  bodega: document.getElementById('bodegaValue'),
  faltantes: document.getElementById('faltantesValue'),
};

const pedidosTableBody = document.getElementById('pedidosTableBody');
const bodegaTableBody = document.getElementById('bodegaTableBody');
const refreshButton = document.getElementById('refreshButton');
const downloadExcelButton = document.getElementById('downloadExcelButton');
const statusBanner = document.getElementById('statusBanner');
const chatForm = document.getElementById('chatForm');
const chatInput = document.getElementById('chatInput');
const sendChatButton = document.getElementById('sendChatButton');
const chatMessages = document.getElementById('chatMessages');

let conversationId = null;

function showStatus(message, type = 'success') {
  statusBanner.textContent = message;
  statusBanner.classList.remove('hidden', 'success', 'error');
  statusBanner.classList.add(type);
}

function hideStatus() {
  statusBanner.classList.add('hidden');
}

function formatNumber(value) {
  if (value === null || value === undefined || value === '') return '--';
  return Number(value).toLocaleString('es-MX');
}

function toProductParts(productName) {
  const [codigo, ...rest] = String(productName).split(' - ');
  return {
    codigo: codigo || '--',
    nombre: rest.join(' - ') || codigo || '--',
  };
}

function renderSummary(dashboardData) {
  const resumen = dashboardData?.resumen || {};
  const productoResumen = dashboardData?.reposicion?.resumen_por_producto || [];

  summaryEls.tiendas.textContent = formatNumber(resumen.tiendas || 0);
  summaryEls.productos.textContent = formatNumber(resumen.productos || 0);
  summaryEls.inventarioTiendas.textContent = formatNumber(resumen.inventario_tiendas || 0);

  const inventarioBodega = productoResumen.reduce((sum, item) => {
    return sum + Number(item['Inventario disponible en bodega'] || 0);
  }, 0);
  const productosConFaltantes = productoResumen.filter((item) => {
    return item['Existe inventario suficiente'] === false;
  }).length;

  summaryEls.bodega.textContent = formatNumber(inventarioBodega || resumen.inventario_bodega || 0);
  summaryEls.faltantes.textContent = formatNumber(productosConFaltantes);
}

function renderBarChart(containerId, data, valueKey, labelKey) {
  const container = document.getElementById(containerId);
  if (!container) {
    return;
  }

  if (!data || data.length === 0) {
    container.innerHTML = '<div class="empty-state">Sin datos disponibles.</div>';
    return;
  }

  const maxValue = Math.max(...data.map((item) => Number(item[valueKey] || 0)), 1);

  const fragment = document.createDocumentFragment();

  data.forEach((item) => {
    const label = item[labelKey] || '--';
    const value = Number(item[valueKey] || 0);
    const width = Math.max((value / maxValue) * 100, 8);

    const row = document.createElement('div');
    row.className = 'chart-row';

    const chartLabel = document.createElement('div');
    chartLabel.className = 'chart-label';

    const labelSpan = document.createElement('span');
    labelSpan.textContent = String(label);

    const valueStrong = document.createElement('strong');
    valueStrong.textContent = formatNumber(value);

    chartLabel.appendChild(labelSpan);
    chartLabel.appendChild(valueStrong);

    const track = document.createElement('div');
    track.className = 'chart-track';

    const bar = document.createElement('div');
    bar.className = 'chart-bar';
    bar.style.width = `${width}%`;

    track.appendChild(bar);
    row.appendChild(chartLabel);
    row.appendChild(track);
    fragment.appendChild(row);
  });

  container.innerHTML = '';
  container.appendChild(fragment);
}

function renderInventoryCharts(reposicionData) {
  const resumenProducto = reposicionData?.resumen_por_producto || [];
  const detalleTienda = reposicionData?.detalle_por_tienda || [];

  const flavorData = resumenProducto.map((item) => ({
    Producto: item.Producto || '--',
    'Inventario disponible en bodega': Number(item['Inventario disponible en bodega'] || 0),
  }));

  const storeMap = {};
  detalleTienda.forEach((item) => {
    const tienda = item.Tienda || '--';
    const cantidad = Number(item['Inventario actual'] || 0);
    storeMap[tienda] = (storeMap[tienda] || 0) + cantidad;
  });

  const storeData = Object.entries(storeMap).map(([tienda, cantidad]) => ({
    Tienda: tienda,
    cantidad,
  }));

  renderBarChart('inventoryByFlavorChart', flavorData, 'Inventario disponible en bodega', 'Producto');
  renderBarChart('inventoryByStoreChart', storeData, 'cantidad', 'Tienda');
}

function renderPedidosSugeridos(detalle) {
  if (!detalle || detalle.length === 0) {
    pedidosTableBody.innerHTML = '<tr><td colspan="7" class="empty-state">No hay datos disponibles.</td></tr>';
    return;
  }

  pedidosTableBody.innerHTML = detalle
    .map((item) => {
      const { codigo, nombre } = toProductParts(item.Producto || '');
      return `
        <tr>
          <td>${item.Tienda || '--'}</td>
          <td>${codigo}</td>
          <td>${nombre}</td>
          <td>${formatNumber(item['Inventario actual'] || 0)}</td>
          <td>${formatNumber(item['Demanda proyectada a 7 días'] || 0)}</td>
          <td>${formatNumber(item['Pedido sugerido'] || 0)}</td>
          <td>${formatNumber(item['Cantidad que podría surtirse'] || 0)}</td>
        </tr>
      `;
    })
    .join('');
}

function renderBodega(resumenProducto) {
  if (!resumenProducto || resumenProducto.length === 0) {
    bodegaTableBody.innerHTML = '<tr><td colspan="6" class="empty-state">No hay inventario disponible en bodega.</td></tr>';
    return;
  }

  bodegaTableBody.innerHTML = resumenProducto
    .map((item) => {
      const suficiente = item['Existe inventario suficiente'] === true;
      const badgeClass = suficiente ? 'success' : 'warning';
      const badgeText = suficiente ? 'Suficiente' : 'Faltante';
      return `
        <tr>
          <td>${item.Producto || '--'}</td>
          <td>${formatNumber(item['Inventario disponible en bodega'] || 0)}</td>
          <td>${formatNumber(item['Necesidad total de las tiendas'] || 0)}</td>
          <td>${formatNumber(item['Cantidad que puede surtirse'] || 0)}</td>
          <td>${formatNumber(item['Cantidad faltante'] || 0)}</td>
          <td><span class="badge ${badgeClass}">${badgeText}</span></td>
        </tr>
      `;
    })
    .join('');
}

async function loadDashboard() {
  hideStatus();
  showStatus('Actualizando datos...', 'success');

  try {
    const [dashboardResponse, reposicionResponse] = await Promise.all([
      fetch('/api/dashboard'),
      fetch('/api/reposicion'),
    ]);

    if (!dashboardResponse.ok || !reposicionResponse.ok) {
      throw new Error(
        `Error al cargar los datos. Dashboard: ${dashboardResponse.status}. Reposición: ${reposicionResponse.status}.`
      );
    }

    const dashboardData = await dashboardResponse.json();
    const reposicionData = await reposicionResponse.json();

    const mergedData = {
      ...dashboardData,
      reposicion: {
        ...(dashboardData.reposicion || {}),
        detalle_por_tienda: reposicionData.detalle_por_tienda || [],
        resumen_por_producto: reposicionData.resumen_por_producto || [],
      },
    };

    renderSummary(mergedData);
    renderPedidosSugeridos(mergedData.reposicion.detalle_por_tienda);
    renderBodega(mergedData.reposicion.resumen_por_producto);
    renderInventoryCharts(mergedData.reposicion);

    showStatus('Datos actualizados correctamente.', 'success');
  } catch (error) {
    console.error(error);
    showStatus('No se pudieron cargar los datos. Verifica que la API esté disponible.', 'error');
    pedidosTableBody.innerHTML = '<tr><td colspan="7" class="empty-state">Error al cargar los pedidos sugeridos.</td></tr>';
    bodegaTableBody.innerHTML = '<tr><td colspan="6" class="empty-state">Error al cargar la disponibilidad en bodega.</td></tr>';
  }
}

function appendChatMessage(role, message) {
  const wrapper = document.createElement('div');
  wrapper.className = `message ${role}`;

  const label = document.createElement('strong');
  label.textContent = role === 'user' ? 'Usuario:' : 'Agente:';

  const content = document.createElement('span');
  content.textContent = message || 'Sin respuesta.';

  wrapper.appendChild(label);
  wrapper.appendChild(content);
  chatMessages.appendChild(wrapper);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

async function sendChatMessage(event) {
  event.preventDefault();

  const message = chatInput.value.trim();
  if (!message) {
    return;
  }

  appendChatMessage('user', message);
  chatInput.value = '';
  sendChatButton.disabled = true;
  sendChatButton.textContent = 'Enviando...';
  showStatus('El agente está respondiendo...', 'success');

  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        conversation_id: conversationId,
        message,
      }),
    });

    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || 'No se pudo contactar al agente.');
    }

    conversationId = payload.conversation_id;
    appendChatMessage('assistant', payload.response);
    showStatus('Respuesta recibida del agente.', 'success');
  } catch (error) {
    console.error(error);
    appendChatMessage('assistant', `Error: ${error.message}`);
    showStatus('No se pudo contactar al agente persistente de Foundry.', 'error');
  } finally {
    sendChatButton.disabled = false;
    sendChatButton.textContent = 'Enviar';
  }
}

chatForm.addEventListener('submit', sendChatMessage);
chatInput.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    chatForm.requestSubmit();
  }
});

async function downloadExcelReport() {
  try {
    showStatus('Generando reporte Excel...', 'success');
    const response = await fetch('/api/reporte-excel');

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || 'No se pudo generar el reporte Excel.');
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    const dateStamp = new Date().toISOString().slice(0, 10).replace(/-/g, '');
    link.href = url;
    link.download = `Reporte_Gelato_Supply_Chain_${dateStamp}.xlsx`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);

    showStatus('Reporte Excel descargado correctamente.', 'success');
  } catch (error) {
    console.error(error);
    showStatus('No se pudo descargar el reporte Excel.', 'error');
  }
}

refreshButton.addEventListener('click', loadDashboard);
if (downloadExcelButton) {
  downloadExcelButton.addEventListener('click', downloadExcelReport);
}

loadDashboard();
