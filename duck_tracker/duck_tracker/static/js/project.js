/* Project specific Javascript goes here. */

// Notes Modal Script
var notesModal = document.getElementById('notesModal');
notesModal.addEventListener('show.bs.modal', function (event) {
  var button = event.relatedTarget;
  var notes = button.getAttribute('data-notes');

  var modalBody = notesModal.querySelector('#notesModalBody');
  modalBody.textContent = notes || 'No notes available.';
});
