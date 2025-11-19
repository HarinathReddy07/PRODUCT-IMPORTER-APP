// API Configuration
const API_BASE = 'http://localhost:8000/api';
const FLASK_API_BASE = 'http://localhost:5000/api';

// Global state
let currentPage = 1;
let currentFilters = {};
let selectedProducts = new Set();

// Navigation
document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const section = btn.dataset.section;
        switchSection(section);
    });
});

function switchSection(section) {
    // Update nav buttons
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    document.querySelector(`[data-section="${section}"]`).classList.add('active');
    
    // Update sections
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    document.getElementById(`${section}-section`).classList.add('active');
    
    // Load data for section
    if (section === 'dashboard') {
        loadStatistics();
        loadDashboardProducts();
    } else if (section === 'products') {
        loadProducts();
    } else if (section === 'webhooks') {
        loadWebhooks();
    }
}

// Load Statistics
async function loadStatistics() {
    try {
        const response = await fetch(`${API_BASE}/statistics`);
        if (response.ok) {
            const stats = await response.json();
            document.getElementById('stat-total').textContent = stats.total_products || 0;
            document.getElementById('stat-active').textContent = stats.active_products || 0;
            document.getElementById('stat-inactive').textContent = stats.inactive_products || 0;
        }
    } catch (error) {
        console.error('Error loading statistics:', error);
    }
}

// Dashboard Products
let dashboardCurrentPage = 1;
let dashboardCurrentFilters = {};

async function loadDashboardProducts(page = 1) {
    dashboardCurrentPage = page;
    const tbody = document.getElementById('products-tbody-dashboard');
    if (!tbody) return;
    
    tbody.innerHTML = '<tr><td colspan="7" class="loading">Loading products...</td></tr>';
    
    const params = new URLSearchParams({
        page: page,
        per_page: 20,
        ...dashboardCurrentFilters
    });
    
    try {
        const response = await fetch(`${API_BASE}/products?${params}`);
        const data = await response.json();
        
        if (response.ok) {
            displayDashboardProducts(data.items);
            displayDashboardPagination(data);
        } else {
            tbody.innerHTML = '<tr><td colspan="7" class="loading">Error loading products</td></tr>';
        }
    } catch (error) {
        tbody.innerHTML = '<tr><td colspan="7" class="loading">Error loading products</td></tr>';
    }
}

function displayDashboardProducts(products) {
    const tbody = document.getElementById('products-tbody-dashboard');
    if (!tbody) return;
    
    if (products.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="loading">No products found</td></tr>';
        selectedProducts.clear();
        updateDashboardBulkDeleteButton();
        return;
    }
    
    tbody.innerHTML = products.map(product => {
        const isChecked = selectedProducts.has(product.id);
        return `
        <tr>
            <td><input type="checkbox" class="product-checkbox" data-product-id="${product.id}" ${isChecked ? 'checked' : ''} onchange="toggleProductSelection(${product.id})"></td>
            <td>${product.id}</td>
            <td>${escapeHtml(product.sku)}</td>
            <td>${escapeHtml(product.name)}</td>
            <td>${escapeHtml(product.description || '').substring(0, 50)}${product.description && product.description.length > 50 ? '...' : ''}</td>
            <td><span class="status-badge ${product.active ? 'active' : 'inactive'}">${product.active ? 'Active' : 'Inactive'}</span></td>
            <td class="action-buttons-cell">
                <button class="btn btn-primary btn-small" onclick="editProduct(${product.id})">Edit</button>
                <button class="btn btn-danger btn-small" onclick="deleteProduct(${product.id})">Delete</button>
            </td>
        </tr>
    `;
    }).join('');
    
    updateDashboardSelectAllCheckbox();
    updateDashboardBulkDeleteButton();
}

function updateDashboardSelectAllCheckbox() {
    const selectAllCheckbox = document.getElementById('select-all-checkbox-dashboard');
    if (!selectAllCheckbox) return;
    
    const checkboxes = document.querySelectorAll('#products-table-dashboard .product-checkbox');
    
    if (checkboxes.length === 0) {
        selectAllCheckbox.checked = false;
        selectAllCheckbox.indeterminate = false;
        return;
    }
    
    const checkedCount = Array.from(checkboxes).filter(cb => cb.checked).length;
    
    if (checkedCount === 0) {
        selectAllCheckbox.checked = false;
        selectAllCheckbox.indeterminate = false;
    } else if (checkedCount === checkboxes.length) {
        selectAllCheckbox.checked = true;
        selectAllCheckbox.indeterminate = false;
    } else {
        selectAllCheckbox.checked = false;
        selectAllCheckbox.indeterminate = true;
    }
}

function updateDashboardBulkDeleteButton() {
    const bulkDeleteBtn = document.getElementById('bulk-delete-btn-dashboard');
    if (!bulkDeleteBtn) return;
    
    if (selectedProducts.size > 0) {
        bulkDeleteBtn.disabled = false;
        bulkDeleteBtn.textContent = `Delete Selected (${selectedProducts.size})`;
    } else {
        bulkDeleteBtn.disabled = true;
        bulkDeleteBtn.textContent = 'Delete Selected';
    }
}

function displayDashboardPagination(data) {
    const pagination = document.getElementById('pagination-dashboard');
    if (!pagination) return;
    
    const totalPages = data.pages || 1;
    
    if (totalPages <= 1) {
        pagination.innerHTML = '';
        return;
    }
    
    let html = `
        <button ${dashboardCurrentPage === 1 ? 'disabled' : ''} onclick="loadDashboardProducts(${dashboardCurrentPage - 1})">Previous</button>
        <span class="page-info">Page ${dashboardCurrentPage} of ${totalPages} (${data.total} total)</span>
        <button ${dashboardCurrentPage >= totalPages ? 'disabled' : ''} onclick="loadDashboardProducts(${dashboardCurrentPage + 1})">Next</button>
    `;
    
    pagination.innerHTML = html;
}

// Dashboard Filters
document.getElementById('apply-filters-dashboard')?.addEventListener('click', () => {
    dashboardCurrentFilters = {
        sku: document.getElementById('filter-sku-dashboard')?.value || '',
        name: document.getElementById('filter-name-dashboard')?.value || '',
        active: document.getElementById('filter-active-dashboard')?.value || undefined
    };
    loadDashboardProducts(1);
});

document.getElementById('clear-filters-dashboard')?.addEventListener('click', () => {
    if (document.getElementById('filter-sku-dashboard')) document.getElementById('filter-sku-dashboard').value = '';
    if (document.getElementById('filter-name-dashboard')) document.getElementById('filter-name-dashboard').value = '';
    if (document.getElementById('filter-active-dashboard')) document.getElementById('filter-active-dashboard').value = '';
    dashboardCurrentFilters = {};
    loadDashboardProducts(1);
});

// Dashboard Select All
document.getElementById('select-all-checkbox-dashboard')?.addEventListener('change', function() {
    const checkboxes = document.querySelectorAll('#products-table-dashboard .product-checkbox');
    checkboxes.forEach(checkbox => {
        checkbox.checked = this.checked;
        const productId = parseInt(checkbox.dataset.productId);
        if (this.checked) {
            selectedProducts.add(productId);
        } else {
            selectedProducts.delete(productId);
        }
    });
    updateDashboardBulkDeleteButton();
    updateBulkDeleteButton();
});

// Dashboard Create Product
document.getElementById('create-product-btn-dashboard')?.addEventListener('click', () => {
    openProductModal();
});

// Dashboard Bulk Delete
document.getElementById('bulk-delete-btn-dashboard')?.addEventListener('click', () => {
    const selectedCount = selectedProducts.size;
    if (selectedCount === 0) {
        showNotification('Please select products to delete', 'error');
        return;
    }
    
    openConfirmModal(
        `Are you sure you want to delete ${selectedCount} selected product(s)? This action cannot be undone.`,
        async () => {
            try {
                const productIds = Array.from(selectedProducts);
                const response = await fetch(`${API_BASE}/products/bulk-delete`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ product_ids: productIds })
                });
                
                if (response.ok) {
                    const result = await response.json();
                    showNotification(`Successfully deleted ${result.deleted_count} product(s)`, 'success');
                    selectedProducts.clear();
                    loadStatistics();
                    loadDashboardProducts(dashboardCurrentPage);
                    loadProducts(currentPage);
                } else {
                    const error = await response.json();
                    showNotification(error.detail || 'Error deleting products', 'error');
                }
            } catch (error) {
                showNotification('Error deleting products', 'error');
            }
        }
    );
});

// File Upload
const fileInput = document.getElementById('file-input');
const uploadProgress = document.getElementById('upload-progress');
const progressBar = document.getElementById('progress-bar');
const progressPercentage = document.getElementById('progress-percentage');
const progressStatus = document.getElementById('progress-status');
const progressMessage = document.getElementById('progress-message');
const uploadResults = document.getElementById('upload-results');

// Handle upload area (works for both dashboard and regular views)
function setupUploadArea() {
    const uploadArea = document.getElementById('upload-area');
    if (!uploadArea) return;
    
    uploadArea.addEventListener('click', () => fileInput.click());
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.style.borderColor = '#138496';
    });
    uploadArea.addEventListener('dragleave', () => {
        uploadArea.style.borderColor = '#17a2b8';
    });
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.style.borderColor = '#17a2b8';
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            fileInput.files = files;
            handleFileUpload(files[0]);
        }
    });
}

setupUploadArea();

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFileUpload(e.target.files[0]);
    }
});

async function handleFileUpload(file) {
    if (!file.name.endsWith('.csv')) {
        showNotification('Please upload a CSV file', 'error');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch(`${FLASK_API_BASE}/upload`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok) {
            if (uploadProgress) uploadProgress.style.display = 'block';
            if (progressBar) progressBar.style.width = '0%';
            if (progressPercentage) progressPercentage.textContent = '0%';
            if (progressStatus) progressStatus.textContent = 'Initializing...';
            if (progressMessage) progressMessage.textContent = 'Upload started...';
            if (uploadResults) uploadResults.style.display = 'none';
            
            // Start SSE connection for progress updates
            startProgressStream(data.task_id);
        } else {
            showNotification(data.error || 'Upload failed', 'error');
        }
    } catch (error) {
        showNotification('Error uploading file: ' + error.message, 'error');
    }
}

function startProgressStream(taskId) {
    const eventSource = new EventSource(`${FLASK_API_BASE}/task/${taskId}/stream`);
    
    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        // Update progress elements (works for both compact and regular views)
        if (progressBar) progressBar.style.width = data.progress + '%';
        if (progressPercentage) progressPercentage.textContent = data.progress + '%';
        if (progressStatus) progressStatus.textContent = data.status;
        if (progressMessage) progressMessage.textContent = data.message;
        
        if (uploadProgress) uploadProgress.style.display = 'block';
        
        if (data.state === 'SUCCESS') {
            eventSource.close();
            displayUploadResults(data.result);
            showNotification('File uploaded successfully!', 'success');
            loadStatistics();
            loadDashboardProducts();
        } else if (data.state === 'FAILURE' || data.state === 'ERROR') {
            eventSource.close();
            showNotification(data.error || data.message || 'Upload failed', 'error');
            if (uploadResults) {
                uploadResults.style.display = 'block';
                uploadResults.className = 'upload-results error';
                uploadResults.innerHTML = `
                    <h4>Upload Failed</h4>
                    <p>${data.error || data.message || 'Unknown error'}</p>
                `;
            }
        }
    };
    
    eventSource.onerror = () => {
        eventSource.close();
        // Fallback to polling
        pollTaskStatus(taskId);
    };
}

function pollTaskStatus(taskId) {
    const interval = setInterval(async () => {
        try {
            const response = await fetch(`${FLASK_API_BASE}/task/${taskId}/status`);
            const data = await response.json();
            
            if (progressBar) progressBar.style.width = data.progress + '%';
            if (progressPercentage) progressPercentage.textContent = data.progress + '%';
            if (progressStatus) progressStatus.textContent = data.status;
            if (progressMessage) progressMessage.textContent = data.message;
            
            if (uploadProgress) uploadProgress.style.display = 'block';
            
            if (data.state === 'SUCCESS') {
                clearInterval(interval);
                displayUploadResults(data.result);
                showNotification('File uploaded successfully!', 'success');
                loadStatistics();
                loadDashboardProducts();
            } else if (data.state === 'FAILURE' || data.state === 'ERROR') {
                clearInterval(interval);
                showNotification(data.error || data.message || 'Upload failed', 'error');
            }
        } catch (error) {
            console.error('Error polling task status:', error);
        }
    }, 1000);
}

function displayUploadResults(result) {
    if (!uploadResults) return;
    uploadResults.style.display = 'block';
    uploadResults.className = 'upload-results';
    uploadResults.innerHTML = `
        <h4>Import Complete</h4>
        <ul>
            <li><strong>Processed:</strong> ${result.processed || 0} products</li>
            <li><strong>Created:</strong> ${result.created || 0} products</li>
            <li><strong>Updated:</strong> ${result.updated || 0} products</li>
            ${result.total_errors > 0 ? `<li><strong>Errors:</strong> ${result.total_errors} errors</li>` : ''}
        </ul>
        ${result.errors && result.errors.length > 0 ? `
            <h5>Sample Errors:</h5>
            <ul>
                ${result.errors.slice(0, 10).map(err => `<li>${err}</li>`).join('')}
            </ul>
        ` : ''}
    `;
}

// Products Management
async function loadProducts(page = 1) {
    currentPage = page;
    const tbody = document.getElementById('products-tbody');
    tbody.innerHTML = '<tr><td colspan="7" class="loading">Loading products...</td></tr>';
    
    const params = new URLSearchParams({
        page: page,
        per_page: 50,
        ...currentFilters
    });
    
    try {
        const response = await fetch(`${API_BASE}/products?${params}`);
        const data = await response.json();
        
        if (response.ok) {
            displayProducts(data.items);
            displayPagination(data);
        } else {
            tbody.innerHTML = '<tr><td colspan="7" class="loading">Error loading products</td></tr>';
        }
    } catch (error) {
        tbody.innerHTML = '<tr><td colspan="7" class="loading">Error loading products</td></tr>';
    }
}

function displayProducts(products) {
    const tbody = document.getElementById('products-tbody');
    
    if (products.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="loading">No products found</td></tr>';
        selectedProducts.clear();
        updateBulkDeleteButton();
        return;
    }
    
    tbody.innerHTML = products.map(product => {
        const isChecked = selectedProducts.has(product.id);
        return `
        <tr>
            <td><input type="checkbox" class="product-checkbox" data-product-id="${product.id}" ${isChecked ? 'checked' : ''} onchange="toggleProductSelection(${product.id})"></td>
            <td>${product.id}</td>
            <td>${escapeHtml(product.sku)}</td>
            <td>${escapeHtml(product.name)}</td>
            <td>${escapeHtml(product.description || '')}</td>
            <td><span class="status-badge ${product.active ? 'active' : 'inactive'}">${product.active ? 'Active' : 'Inactive'}</span></td>
            <td class="action-buttons-cell">
                <button class="btn btn-primary btn-small" onclick="editProduct(${product.id})">Edit</button>
                <button class="btn btn-danger btn-small" onclick="deleteProduct(${product.id})">Delete</button>
            </td>
        </tr>
    `;
    }).join('');
    
    updateSelectAllCheckbox();
    updateBulkDeleteButton();
}

function toggleProductSelection(productId) {
    const checkbox = document.querySelector(`.product-checkbox[data-product-id="${productId}"]`);
    if (checkbox.checked) {
        selectedProducts.add(productId);
    } else {
        selectedProducts.delete(productId);
    }
    updateSelectAllCheckbox();
    updateBulkDeleteButton();
    updateDashboardSelectAllCheckbox();
    updateDashboardBulkDeleteButton();
}

function updateSelectAllCheckbox() {
    const selectAllCheckbox = document.getElementById('select-all-checkbox');
    const checkboxes = document.querySelectorAll('.product-checkbox');
    
    if (checkboxes.length === 0) {
        selectAllCheckbox.checked = false;
        selectAllCheckbox.indeterminate = false;
        return;
    }
    
    const checkedCount = Array.from(checkboxes).filter(cb => cb.checked).length;
    
    if (checkedCount === 0) {
        selectAllCheckbox.checked = false;
        selectAllCheckbox.indeterminate = false;
    } else if (checkedCount === checkboxes.length) {
        selectAllCheckbox.checked = true;
        selectAllCheckbox.indeterminate = false;
    } else {
        selectAllCheckbox.checked = false;
        selectAllCheckbox.indeterminate = true;
    }
}

function updateBulkDeleteButton() {
    const bulkDeleteBtn = document.getElementById('bulk-delete-btn');
    if (selectedProducts.size > 0) {
        bulkDeleteBtn.disabled = false;
        bulkDeleteBtn.textContent = `Delete Selected Products (${selectedProducts.size})`;
    } else {
        bulkDeleteBtn.disabled = true;
        bulkDeleteBtn.textContent = 'Delete Selected Products';
    }
}

// Select All functionality
document.getElementById('select-all-checkbox').addEventListener('change', function() {
    const checkboxes = document.querySelectorAll('.product-checkbox');
    checkboxes.forEach(checkbox => {
        checkbox.checked = this.checked;
        const productId = parseInt(checkbox.dataset.productId);
        if (this.checked) {
            selectedProducts.add(productId);
        } else {
            selectedProducts.delete(productId);
        }
    });
    updateBulkDeleteButton();
});

function displayPagination(data) {
    const pagination = document.getElementById('pagination');
    const totalPages = data.pages || 1;
    
    if (totalPages <= 1) {
        pagination.innerHTML = '';
        return;
    }
    
    let html = `
        <button ${currentPage === 1 ? 'disabled' : ''} onclick="loadProducts(${currentPage - 1})">Previous</button>
        <span class="page-info">Page ${currentPage} of ${totalPages} (${data.total} total)</span>
        <button ${currentPage >= totalPages ? 'disabled' : ''} onclick="loadProducts(${currentPage + 1})">Next</button>
    `;
    
    pagination.innerHTML = html;
}

// Filters
document.getElementById('apply-filters').addEventListener('click', () => {
    currentFilters = {
        sku: document.getElementById('filter-sku').value,
        name: document.getElementById('filter-name').value,
        description: document.getElementById('filter-description').value,
        active: document.getElementById('filter-active').value || undefined
    };
    loadProducts(1);
});

document.getElementById('clear-filters').addEventListener('click', () => {
    document.getElementById('filter-sku').value = '';
    document.getElementById('filter-name').value = '';
    document.getElementById('filter-description').value = '';
    document.getElementById('filter-active').value = '';
    currentFilters = {};
    loadProducts(1);
});

// Product CRUD
document.getElementById('create-product-btn').addEventListener('click', () => {
    openProductModal();
});

function openProductModal(product = null) {
    const modal = document.getElementById('product-modal');
    const form = document.getElementById('product-form');
    const title = document.getElementById('product-modal-title');
    
    if (product) {
        title.textContent = 'Edit Product';
        document.getElementById('product-id').value = product.id;
        document.getElementById('product-sku').value = product.sku;
        document.getElementById('product-sku').disabled = true;
        document.getElementById('product-name').value = product.name;
        document.getElementById('product-description').value = product.description || '';
        document.getElementById('product-active').checked = product.active;
    } else {
        title.textContent = 'Create Product';
        form.reset();
        document.getElementById('product-id').value = '';
        document.getElementById('product-sku').disabled = false;
    }
    
    modal.style.display = 'block';
}

async function editProduct(id) {
    try {
        const response = await fetch(`${API_BASE}/products/${id}`);
        const product = await response.json();
        if (response.ok) {
            openProductModal(product);
        }
    } catch (error) {
        showNotification('Error loading product', 'error');
    }
}

document.getElementById('product-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const id = document.getElementById('product-id').value;
    const productData = {
        sku: document.getElementById('product-sku').value,
        name: document.getElementById('product-name').value,
        description: document.getElementById('product-description').value,
        active: document.getElementById('product-active').checked
    };
    
    try {
        let response;
        if (id) {
            // Update
            const updateData = { ...productData };
            delete updateData.sku; // SKU cannot be updated
            response = await fetch(`${API_BASE}/products/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(updateData)
            });
        } else {
            // Create
            response = await fetch(`${API_BASE}/products`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(productData)
            });
        }
        
        if (response.ok) {
            closeModal('product-modal');
            showNotification(id ? 'Product updated successfully' : 'Product created successfully', 'success');
            loadStatistics();
            loadProducts(currentPage);
            loadDashboardProducts(dashboardCurrentPage);
        } else {
            const error = await response.json();
            showNotification(error.detail || 'Error saving product', 'error');
        }
    } catch (error) {
        showNotification('Error saving product', 'error');
    }
});

async function deleteProduct(id) {
    if (!confirm('Are you sure you want to delete this product?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/products/${id}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            selectedProducts.delete(id);
            showNotification('Product deleted successfully', 'success');
            loadStatistics();
            loadProducts(currentPage);
            loadDashboardProducts(dashboardCurrentPage);
        } else {
            showNotification('Error deleting product', 'error');
        }
    } catch (error) {
        showNotification('Error deleting product', 'error');
    }
}

// Bulk Delete Selected Products
document.getElementById('bulk-delete-btn').addEventListener('click', () => {
    const selectedCount = selectedProducts.size;
    if (selectedCount === 0) {
        showNotification('Please select products to delete', 'error');
        return;
    }
    
    openConfirmModal(
        `Are you sure you want to delete ${selectedCount} selected product(s)? This action cannot be undone.`,
        async () => {
            try {
                const productIds = Array.from(selectedProducts);
                const response = await fetch(`${API_BASE}/products/bulk-delete`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ product_ids: productIds })
                });
                
                if (response.ok) {
                    const result = await response.json();
                    showNotification(`Successfully deleted ${result.deleted_count} product(s)`, 'success');
                    selectedProducts.clear();
                    loadStatistics();
                    loadProducts(currentPage);
                    loadDashboardProducts(dashboardCurrentPage);
                } else {
                    const error = await response.json();
                    showNotification(error.detail || 'Error deleting products', 'error');
                }
            } catch (error) {
                showNotification('Error deleting products', 'error');
            }
        }
    );
});


// Webhooks Management
async function loadWebhooks() {
    const tbody = document.getElementById('webhooks-tbody');
    tbody.innerHTML = '<tr><td colspan="5" class="loading">Loading webhooks...</td></tr>';
    
    try {
        const response = await fetch(`${API_BASE}/webhooks`);
        const webhooks = await response.json();
        
        if (response.ok) {
            displayWebhooks(webhooks);
        } else {
            tbody.innerHTML = '<tr><td colspan="5" class="loading">Error loading webhooks</td></tr>';
        }
    } catch (error) {
        tbody.innerHTML = '<tr><td colspan="5" class="loading">Error loading webhooks</td></tr>';
    }
}

function displayWebhooks(webhooks) {
    const tbody = document.getElementById('webhooks-tbody');
    
    if (webhooks.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="loading">No webhooks found</td></tr>';
        return;
    }
    
    tbody.innerHTML = webhooks.map(webhook => `
        <tr>
            <td>${webhook.id}</td>
            <td>${escapeHtml(webhook.url)}</td>
            <td>${escapeHtml(webhook.event_type)}</td>
            <td><span class="status-badge ${webhook.enabled ? 'enabled' : 'disabled'}">${webhook.enabled ? 'Enabled' : 'Disabled'}</span></td>
            <td class="action-buttons-cell">
                <button class="btn btn-success btn-small" onclick="testWebhook(${webhook.id})">Test</button>
                <button class="btn btn-primary btn-small" onclick="editWebhook(${webhook.id})">Edit</button>
                <button class="btn btn-danger btn-small" onclick="deleteWebhook(${webhook.id})">Delete</button>
            </td>
        </tr>
    `).join('');
}

document.getElementById('create-webhook-btn').addEventListener('click', () => {
    openWebhookModal();
});

function openWebhookModal(webhook = null) {
    const modal = document.getElementById('webhook-modal');
    const form = document.getElementById('webhook-form');
    const title = document.getElementById('webhook-modal-title');
    
    if (webhook) {
        title.textContent = 'Edit Webhook';
        document.getElementById('webhook-id').value = webhook.id;
        document.getElementById('webhook-url').value = webhook.url;
        document.getElementById('webhook-event-type').value = webhook.event_type;
        document.getElementById('webhook-secret').value = webhook.secret || '';
        document.getElementById('webhook-enabled').checked = webhook.enabled;
    } else {
        title.textContent = 'Create Webhook';
        form.reset();
        document.getElementById('webhook-id').value = '';
    }
    
    modal.style.display = 'block';
}

async function editWebhook(id) {
    try {
        const response = await fetch(`${API_BASE}/webhooks/${id}`);
        const webhook = await response.json();
        if (response.ok) {
            openWebhookModal(webhook);
        }
    } catch (error) {
        showNotification('Error loading webhook', 'error');
    }
}

async function testWebhook(id) {
    try {
        showNotification('Testing webhook...', 'info');
        const response = await fetch(`${API_BASE}/webhooks/${id}/test`, {
            method: 'POST'
        });
        const result = await response.json();
        
        if (result.success) {
            showNotification(`Webhook test successful! Status: ${result.status_code}, Response time: ${result.response_time?.toFixed(2)}s`, 'success');
        } else {
            showNotification(`Webhook test failed: ${result.error || 'Unknown error'}`, 'error');
        }
    } catch (error) {
        showNotification('Error testing webhook', 'error');
    }
}

document.getElementById('webhook-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const id = document.getElementById('webhook-id').value;
    const webhookData = {
        url: document.getElementById('webhook-url').value,
        event_type: document.getElementById('webhook-event-type').value,
        secret: document.getElementById('webhook-secret').value || null,
        enabled: document.getElementById('webhook-enabled').checked
    };
    
    try {
        let response;
        if (id) {
            response = await fetch(`${API_BASE}/webhooks/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(webhookData)
            });
        } else {
            response = await fetch(`${API_BASE}/webhooks`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(webhookData)
            });
        }
        
        if (response.ok) {
            closeModal('webhook-modal');
            showNotification(id ? 'Webhook updated successfully' : 'Webhook created successfully', 'success');
            loadWebhooks();
        } else {
            const error = await response.json();
            showNotification(error.detail || 'Error saving webhook', 'error');
        }
    } catch (error) {
        showNotification('Error saving webhook', 'error');
    }
});

async function deleteWebhook(id) {
    if (!confirm('Are you sure you want to delete this webhook?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/webhooks/${id}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showNotification('Webhook deleted successfully', 'success');
            loadWebhooks();
        } else {
            showNotification('Error deleting webhook', 'error');
        }
    } catch (error) {
        showNotification('Error deleting webhook', 'error');
    }
}

// Modal Management
function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

document.querySelectorAll('.close').forEach(closeBtn => {
    closeBtn.addEventListener('click', () => {
        closeBtn.closest('.modal').style.display = 'none';
    });
});

document.getElementById('cancel-product').addEventListener('click', () => {
    closeModal('product-modal');
});

document.getElementById('cancel-webhook').addEventListener('click', () => {
    closeModal('webhook-modal');
});

window.onclick = (event) => {
    if (event.target.classList.contains('modal')) {
        event.target.style.display = 'none';
    }
};

// Confirmation Modal
function openConfirmModal(message, onConfirm) {
    const modal = document.getElementById('confirm-modal');
    document.getElementById('confirm-message').textContent = message;
    modal.style.display = 'block';
    
    const confirmBtn = document.getElementById('confirm-ok');
    const cancelBtn = document.getElementById('confirm-cancel');
    
    // Remove old listeners
    const newConfirmBtn = confirmBtn.cloneNode(true);
    const newCancelBtn = cancelBtn.cloneNode(true);
    confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);
    cancelBtn.parentNode.replaceChild(newCancelBtn, cancelBtn);
    
    newConfirmBtn.addEventListener('click', () => {
        closeModal('confirm-modal');
        onConfirm();
    });
    
    newCancelBtn.addEventListener('click', () => {
        closeModal('confirm-modal');
    });
}

// Notifications
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 5000);
}

// Utility
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize
loadStatistics();
loadDashboardProducts();
loadProducts();

