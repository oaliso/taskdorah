const owner = document.querySelector('select#usuario_id');
const contact = document.querySelector('#contato_id');
if (owner && contact) {
  const filterContacts = () => {
    for (const option of contact.options) {
      if (!option.value) continue;
      option.hidden = option.dataset.owner !== owner.value;
      option.disabled = option.hidden;
      if (option.selected && option.disabled) contact.value = '';
    }
  };
  owner.addEventListener('change', filterContacts);
  filterContacts();
}
