# Admin Edit Function Patterns - Best Practices

## ✅ **Dynamic Field Mapping Pattern**

### **NEVER** hard-code field names in edit functions. Always use dynamic field mapping.

### **Correct Pattern:**
```javascript
function edit[TableName](id) {
    const item = window.all[TableName]s.find(item => item.id == id);
    if (!item) {
        alert('[TableName] not found');
        return;
    }
    
    // Dynamic field mapping - NEVER hard-code field names
    const fieldMapping = {
        'id': 'edit[TableName]Id',
        'name': 'edit[TableName]Name',
        'field1': 'edit[TableName]Field1',
        'field2': 'edit[TableName]Field2',
        // Add all fields here
    };
    
    // Populate edit form dynamically
    Object.entries(fieldMapping).forEach(([dataField, formField]) => {
        const element = document.getElementById(formField);
        if (element) {
            if (element.type === 'checkbox') {
                element.checked = item[dataField] || false;
            } else {
                element.value = item[dataField] || '';
            }
        }
    });
    
    // Show the modal
    document.getElementById('edit[TableName]Modal').style.display = 'block';
}
```

### **Benefits of Dynamic Field Mapping:**
1. **Maintainable**: Easy to add/remove fields without changing multiple places
2. **Flexible**: Works with different field types (text, checkbox, select, etc.)
3. **Error-resistant**: Won't break if form field IDs change
4. **Scalable**: Easy to extend for new tables
5. **Consistent**: Same pattern across all tables

### **Field Type Handling:**
```javascript
// Handle different input types automatically
if (element.type === 'checkbox') {
    element.checked = item[dataField] || false;
} else {
    element.value = item[dataField] || '';
}
```

### **Example Implementations:**

#### **Venue Edit Function:**
```javascript
function editVenue(id) {
    const venue = window.allVenues.find(v => v.id == id);
    if (!venue) {
        alert('Venue not found');
        return;
    }
    
    const fieldMapping = {
        'id': 'editVenueId',
        'name': 'editVenueName',
        'venue_type': 'editVenueType',
        'address': 'editVenueAddress',
        'description': 'editVenueDescription',
        'opening_hours': 'editVenueHours',
        'phone_number': 'editVenuePhone',
        'email': 'editVenueEmail',
        'website_url': 'editVenueWebsite',
        'admission_fee': 'editVenueAdmission'
    };
    
    Object.entries(fieldMapping).forEach(([dataField, formField]) => {
        const element = document.getElementById(formField);
        if (element) {
            if (element.type === 'checkbox') {
                element.checked = venue[dataField] || false;
            } else {
                element.value = venue[dataField] || '';
            }
        }
    });
    
    document.getElementById('editVenueModal').style.display = 'block';
}
```

#### **Event Edit Function:**
```javascript
function editEvent(id) {
    const event = window.allEvents.find(e => e.id == id);
    if (!event) {
        alert('Event not found');
        return;
    }
    
    const fieldMapping = {
        'id': 'editEventId',
        'title': 'editEventTitle',
        'description': 'editEventDescription',
        'start_date': 'editEventStartDate',
        'start_time': 'editEventStartTime',
        'end_time': 'editEventEndTime',
        'event_type': 'editEventType'
    };
    
    Object.entries(fieldMapping).forEach(([dataField, formField]) => {
        const element = document.getElementById(formField);
        if (element) {
            if (element.type === 'checkbox') {
                element.checked = event[dataField] || false;
            } else {
                element.value = event[dataField] || '';
            }
        }
    });
    
    document.getElementById('editEventModal').style.display = 'block';
}
```

### **❌ Anti-Pattern - DON'T DO THIS:**
```javascript
// BAD: Hard-coded field names
function editVenue(id) {
    const venue = window.allVenues.find(v => v.id == id);
    
    document.getElementById('editVenueId').value = venue.id;
    document.getElementById('editVenueName').value = venue.name;
    document.getElementById('editVenueType').value = venue.venue_type || '';
    document.getElementById('editVenueAddress').value = venue.address || '';
    // ... more hard-coded fields
}
```

### **Why Dynamic Mapping is Better:**
1. **Single Source of Truth**: Field mappings defined in one place
2. **Easy Maintenance**: Add new fields by updating the mapping object
3. **Type Safety**: Automatic handling of different input types
4. **Error Prevention**: Won't break if form structure changes
5. **Code Reusability**: Same pattern works for all tables

### **For Future Tables:**
1. Create the modal form with consistent ID naming: `edit[TableName][FieldName]`
2. Use the dynamic field mapping pattern
3. Define the mapping object with all fields
4. Use the generic populate logic
5. Test with different field types (text, checkbox, select, etc.)

### **Key Rules:**
1. **NEVER** hard-code field names in edit functions
2. **ALWAYS** use dynamic field mapping with Object.entries()
3. **ALWAYS** handle different input types (checkbox vs text)
4. **ALWAYS** check if element exists before setting values
5. **ALWAYS** provide fallback values with `|| ''` or `|| false`

This pattern ensures maintainable, scalable, and error-resistant edit functionality across all admin tables.





