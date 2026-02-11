/**
 * Formset Handler for Flock Income Calculator
 * Manages adding/removing rows for egg types and expenses
 * Uses prefixes: "eggs" and "expenses"
 */

document.addEventListener('DOMContentLoaded', function () {
  console.log('[Formset] Initializing formset handlers...');
  
  // Egg Type Formset Handler
  initializeEggTypeFormset();

  // Expense Formset Handler
  initializeExpenseFormset();

  // Initial calculations
  updateEggTypePercentages();
  updateExpenseTotal();
  
  console.log('[Formset] Initialization complete');
  
  // Form submit validation: prevent submission if egg percentages > 100
  const incomeForm = document.getElementById('income-form');
  if (incomeForm) {
    incomeForm.addEventListener('submit', function (e) {
      const total = updateEggTypePercentages();
      if (total > 100) {
        e.preventDefault();
        const errorEl = document.getElementById('percent-error');
        if (errorEl) {
          errorEl.classList.remove('d-none');
        }
        // focus first percent input that's invalid
        const firstInvalid = document.querySelector('#egg-types input[name*="percent"]');
        if (firstInvalid) {
          firstInvalid.focus();
        }
        console.warn('[Formset] Submission prevented: total percent > 100');
      }
    });
  }
});

/**
 * Initialize egg type formset with add/remove handlers
 */
function initializeEggTypeFormset() {
  const addButton = document.getElementById('add-row');
  const eggTypesContainer = document.getElementById('egg-types');

  if (!addButton) {
    console.error('[Formset] Add button not found');
    return;
  }

  if (!eggTypesContainer) {
    console.error('[Formset] Egg types container not found');
    return;
  }

  console.log('[Formset] Found add button and container');

  addButton.addEventListener('click', function (e) {
    e.preventDefault();
    console.log('[Formset] Add button clicked');
    addEggTypeRow();
  });

  // Delegate event handler for remove buttons
  eggTypesContainer.addEventListener('click', function (e) {
    if (e.target.classList.contains('remove-row')) {
      e.preventDefault();
      console.log('[Formset] Remove button clicked');
      removeEggTypeRow(e.target);
    }
  });

  // Add listeners to percent and price inputs for real-time calculation
  eggTypesContainer.addEventListener('input', function (e) {
    if (e.target.name.includes('percent') || e.target.name.includes('price')) {
      updateEggTypePercentages();
    }
  });
}

/**
 * Add a new egg type row
 */
function addEggTypeRow() {
  const eggTypesContainer = document.getElementById('egg-types');
  
  // Try multiple selectors for TOTAL_FORMS (prefix is "eggs")
  let formCountElement = document.getElementById('id_eggs-TOTAL_FORMS');
  if (!formCountElement) {
    formCountElement = document.querySelector('[name="eggs-TOTAL_FORMS"]');
  }

  if (!formCountElement) {
    console.error('[Formset] TOTAL_FORMS field not found');
    console.log('[Formset] Available form fields:', Array.from(document.querySelectorAll('[name*="eggs"]')).map(f => f.name));
    return;
  }

  const currentCount = parseInt(formCountElement.value);
  console.log('[Formset] Current count:', currentCount);

  // Get the last row to clone
  const rows = eggTypesContainer.querySelectorAll('.egg-row');
  if (rows.length === 0) {
    console.error('[Formset] No rows found to clone');
    return;
  }

  const lastRow = rows[rows.length - 1];
  const newRow = lastRow.cloneNode(true);

  // Remove data-fixed attribute if present
  newRow.removeAttribute('data-fixed');

  // Update all form field names and IDs
  newRow.querySelectorAll('input, select, textarea').forEach(function (field) {
    const name = field.getAttribute('name');
    const id = field.getAttribute('id');

    if (name) {
      const newName = name.replace(/eggs-\d+/, `eggs-${currentCount}`);
      field.setAttribute('name', newName);
      console.log('[Formset] Updated name:', name, '->', newName);
    }

    if (id) {
      const newId = id.replace(/id_eggs-\d+/, `id_eggs-${currentCount}`);
      field.setAttribute('id', newId);
      console.log('[Formset] Updated id:', id, '->', newId);
    }

    // Clear field values
    if (field.type !== 'hidden') {
      field.value = '';
    }
  });

  // Update label 'for' attributes
  newRow.querySelectorAll('label').forEach(function (label) {
    const forAttr = label.getAttribute('for');
    if (forAttr) {
      const newFor = forAttr.replace(/id_eggs-\d+/, `id_eggs-${currentCount}`);
      label.setAttribute('for', newFor);
    }
  });

  // Enable remove button for new row
  const removeButton = newRow.querySelector('.remove-row');
  if (removeButton) {
    removeButton.removeAttribute('disabled');
    removeButton.removeAttribute('title');
  }

  // Append the new row
  eggTypesContainer.appendChild(newRow);

  // Update form count
  formCountElement.value = currentCount + 1;
  console.log('[Formset] Updated TOTAL_FORMS to:', currentCount + 1);

  // Update percentages
  updateEggTypePercentages();
}

/**
 * Remove an egg type row
 */
function removeEggTypeRow(button) {
  const row = button.closest('.egg-row');
  const deleteField = row.querySelector('input[type="hidden"][name*="DELETE"]');

  if (deleteField) {
    // Mark as deleted (Django formset way)
    deleteField.value = 'on';
    row.style.display = 'none';
    console.log('[Formset] Marked row as deleted');
  } else {
    // Fallback: just remove the row
    row.remove();
    console.log('[Formset] Removed row directly');
  }

  updateEggTypePercentages();
}

/**
 * Update egg type percentages display and validation
 */
function updateEggTypePercentages() {
  const eggTypesContainer = document.getElementById('egg-types');
  let totalPercent = 0;

  // Calculate total percentage
  eggTypesContainer.querySelectorAll('.egg-row').forEach(function (row) {
    const deleteField = row.querySelector('input[type="hidden"][name*="DELETE"]');
    
    // Skip deleted rows
    if (deleteField && deleteField.value === 'on') {
      return;
    }

    const percentInput = row.querySelector('input[name*="percent"]');
    if (percentInput && percentInput.value) {
      totalPercent += parseFloat(percentInput.value) || 0;
    }
  });

  // Update display
  document.getElementById('current-percent').textContent = totalPercent.toFixed(1);
  document.getElementById('remaining-percent').textContent = Math.max(
    0,
    (100 - totalPercent).toFixed(1)
  );

  // Show error if exceeds 100%
  const errorElement = document.getElementById('percent-error');
  if (totalPercent > 100) {
    errorElement.classList.remove('d-none');
  } else {
    errorElement.classList.add('d-none');
  }
  
  // return total to allow callers (eg. submit validation) to check
  return totalPercent;
}

/**
 * Initialize expense formset with add/remove handlers
 */
function initializeExpenseFormset() {
  const addButton = document.getElementById('add-row-expense');
  const expenseContainer = document.getElementById('expense-types');

  if (!addButton) {
    console.error('[Formset] Expense add button not found');
    return;
  }

  if (!expenseContainer) {
    console.error('[Formset] Expense container not found');
    return;
  }

  console.log('[Formset] Found expense add button and container');

  addButton.addEventListener('click', function (e) {
    e.preventDefault();
    console.log('[Formset] Expense add button clicked');
    addExpenseRow();
  });

  // Delegate event handler for remove buttons
  expenseContainer.addEventListener('click', function (e) {
    if (e.target.classList.contains('remove-row')) {
      e.preventDefault();
      console.log('[Formset] Expense remove button clicked');
      removeExpenseRow(e.target);
    }
  });

  // Add listeners to cost inputs for real-time calculation
  expenseContainer.addEventListener('input', function (e) {
    if (e.target.name.includes('cost')) {
      updateExpenseTotal();
    }
  });
}

/**
 * Add a new expense row
 */
function addExpenseRow() {
  const expenseContainer = document.getElementById('expense-types');
  
  // Try multiple selectors for TOTAL_FORMS (prefix is "expenses")
  let formCountElement = document.getElementById('id_expenses-TOTAL_FORMS');
  if (!formCountElement) {
    formCountElement = document.querySelector('[name="expenses-TOTAL_FORMS"]');
  }

  if (!formCountElement) {
    console.error('[Formset] Expense TOTAL_FORMS field not found');
    console.log('[Formset] Available form fields:', Array.from(document.querySelectorAll('[name*="expenses"]')).map(f => f.name));
    return;
  }

  const currentCount = parseInt(formCountElement.value);
  console.log('[Formset] Current expense count:', currentCount);

  // Get the last row to clone
  const rows = expenseContainer.querySelectorAll('.egg-row');
  if (rows.length === 0) {
    console.error('[Formset] No expense rows found to clone');
    return;
  }

  const lastRow = rows[rows.length - 1];
  const newRow = lastRow.cloneNode(true);

  // Update all form field names and IDs
  newRow.querySelectorAll('input, select, textarea').forEach(function (field) {
    const name = field.getAttribute('name');
    const id = field.getAttribute('id');

    if (name) {
      const newName = name.replace(/expenses-\d+/, `expenses-${currentCount}`);
      field.setAttribute('name', newName);
      console.log('[Formset] Updated expense name:', name, '->', newName);
    }

    if (id) {
      const newId = id.replace(/id_expenses-\d+/, `id_expenses-${currentCount}`);
      field.setAttribute('id', newId);
      console.log('[Formset] Updated expense id:', id, '->', newId);
    }

    // Clear field values
    if (field.type !== 'hidden') {
      field.value = '';
    }
  });

  // Update label 'for' attributes
  newRow.querySelectorAll('label').forEach(function (label) {
    const forAttr = label.getAttribute('for');
    if (forAttr) {
      const newFor = forAttr.replace(/id_expenses-\d+/, `id_expenses-${currentCount}`);
      label.setAttribute('for', newFor);
    }
  });

  // Enable remove button for new row
  const removeButton = newRow.querySelector('.remove-row');
  if (removeButton) {
    removeButton.removeAttribute('disabled');
    removeButton.removeAttribute('title');
  }

  // Append the new row
  expenseContainer.appendChild(newRow);

  // Update form count
  formCountElement.value = currentCount + 1;
  console.log('[Formset] Updated expense TOTAL_FORMS to:', currentCount + 1);

  // Update expense total
  updateExpenseTotal();
}

/**
 * Remove an expense row
 */
function removeExpenseRow(button) {
  const row = button.closest('.egg-row');
  const deleteField = row.querySelector('input[type="hidden"][name*="DELETE"]');

  if (deleteField) {
    // Mark as deleted (Django formset way)
    deleteField.value = 'on';
    row.style.display = 'none';
    console.log('[Formset] Marked expense row as deleted');
  } else {
    // Fallback: just remove the row
    row.remove();
    console.log('[Formset] Removed expense row directly');
  }

  updateExpenseTotal();
}

/**
 * Update total expenses display
 */
function updateExpenseTotal() {
  const expenseContainer = document.getElementById('expense-types');
  let totalExpense = 0;

  expenseContainer.querySelectorAll('.egg-row').forEach(function (row) {
    const deleteField = row.querySelector('input[type="hidden"][name*="DELETE"]');
    
    // Skip deleted rows
    if (deleteField && deleteField.value === 'on') {
      return;
    }

    const costInput = row.querySelector('input[name*="cost"]');
    if (costInput && costInput.value) {
      totalExpense += parseFloat(costInput.value) || 0;
    }
  });

  // Update display with proper formatting
  document.getElementById('total-expenses').textContent = totalExpense.toFixed(2);
}
