# Training Data Upload Utility for Frappe

## Overview
This utility provides functionality to upload and organize machine learning training data (images) and models within the Frappe framework. It's designed specifically for defect detection applications, categorizing images as either "ok" or "defective".

## Features
- Upload multiple training images with labels
- Organize files in a structured folder hierarchy
- Support for uploading trained model files (.h5 format)
- Automatic folder creation and file management
- Integration with Frappe's file system and permissions model

## Function: `upload_training_data`

### Description
Uploads training data (images and labels) to the Frappe file system. Also allows uploading a trained model file in .h5 format.

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `project_name` | str | The name of the project to associate the training data with |
| `training_data` | list | A list of dictionaries containing image data and labels |
| `model_file` | dict (optional) | Dictionary containing model file data and filename |

#### `training_data` format
Each item in the list should be a dictionary with:
- `image` (str): Base64 encoded image data
- `label` (str): The label for the image ('ok' or 'defective')

#### `model_file` format
If provided, should be a dictionary with:
- `file_data` (str): Base64 encoded model file data (.h5 format)
- `file_name` (str): The name of the model file

### Folder Structure
The utility creates the following folder structure:
```
Home/
└── training_data/
    └── [project_name]/
        ├── ok/
        │   └── [image files]
        ├── defective/
        │   └── [image files]
        └── model/
            └── [model files]
```

### Helper Function: `create_folder`

This internal function creates a folder in Frappe's file system if it doesn't exist:

```python
def create_folder(folder_name, parent_folder="Home"):
    """Create a folder in Frappe's file system if it doesn't exist"""
    # Determine the exact parent folder name for querying
    parent_name = parent_folder
    if parent_folder != "Home":
        parent_doc = frappe.get_doc("File", parent_folder)
        parent_name = parent_doc.name
    
    # Check if folder already exists under the parent
    folder_exists = frappe.db.exists(
        "File", 
        {"file_name": folder_name, "folder": parent_name, "is_folder": 1}
    )
    
    if folder_exists:
        return frappe.get_doc(
            "File", 
            {"file_name": folder_name, "folder": parent_name, "is_folder": 1}
        )
    
    # Create new folder
    folder = frappe.new_doc("File")
    folder.file_name = folder_name
    folder.is_folder = 1
    folder.folder = parent_name
    
    # Important: these fields help ensure the folder is visible in File Manager
    folder.is_private = 1
    folder.attached_to_doctype = "Project"
    folder.attached_to_name = project_name
    
    folder.insert(ignore_permissions=True)
    frappe.db.commit()  # Commit immediately to ensure folder is created
    
    return folder
```

### Return Value
Returns a dictionary containing:
- `message`: Success message
- `files`: List of uploaded files with metadata
- `project`: Project name
- `count`: Number of files uploaded
- `folder_path`: Path to the project folder
- `model_file`: Model file information (if uploaded)

### Example Usage
```python
# Example client-side code to call the function
import frappe
import json
import base64

def upload_training_images(project_name, image_files, labels, model_file=None):
    training_data = []
    
    for i, image_file in enumerate(image_files):
        with open(image_file, "rb") as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
            
        training_data.append({
            "image": image_data,
            "label": labels[i]  # 'ok' or 'defective'
        })
    
    model_data = None
    if model_file:
        with open(model_file, "rb") as f:
            model_data = {
                "file_data": base64.b64encode(f.read()).decode('utf-8'),
                "file_name": model_file.split("/")[-1]
            }
    
    result = frappe.call({
        'method': 'your_app.your_module.upload_training_data',
        'args': {
            'project_name': project_name,
            'training_data': json.dumps(training_data),
            'model_file': json.dumps(model_data) if model_data else None
        }
    })
    
    return result
```

## Requirements
- Frappe Framework
- Access to Frappe's file system and database
- Proper permissions to create files and folders

## Notes
- Images are expected to be in PNG format
- Model files should be in .h5 format (Keras/TensorFlow saved models)
- The utility automatically commits changes to the database
- In case of errors, a full rollback is performed

## Error Handling
The utility includes comprehensive error handling:
- Validates that the project exists
- Checks for required fields in training data
- Handles potential exceptions during file operations
- Logs detailed error information to Frappe's error log
