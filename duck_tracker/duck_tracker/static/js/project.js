/* Project specific Javascript goes here. */

// Notes Modal Script
var notesModal = document.getElementById('notesModal');

notesModal.addEventListener('show.bs.modal', function (event) {
  var button = event.relatedTarget;
  var row = button.closest('tr');
  var notesContent = row.querySelector('.notes-content');

  var modalBody = notesModal.querySelector('#notesModalBody');

  if (notesContent) {
    modalBody.innerHTML = notesContent.innerHTML;
  } else {
    modalBody.innerHTML = 'No notes available.';
  }
});
