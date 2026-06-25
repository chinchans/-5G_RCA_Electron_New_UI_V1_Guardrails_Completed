// Get current templates
const templates = JSON.parse(localStorage.getItem('userTemplates') || '{}');

// Templates to remove
const templatesToRemove = ['testting', 'dev'];

// Remove from all roles (tester, developer, analyst)
Object.keys(templates).forEach(role => {
    if (Array.isArray(templates[role])) {
        templates[role] = templates[role].filter(t => !templatesToRemove.includes(t.name));
        console.log(`Removed templates from ${role} role`);
    }
});

// Save back to localStorage
localStorage.setItem('userTemplates', JSON.stringify(templates));

// Show remaining templates
console.log('Remaining templates:', JSON.parse(localStorage.getItem('userTemplates')));