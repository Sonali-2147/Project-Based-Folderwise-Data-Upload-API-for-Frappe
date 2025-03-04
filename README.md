# Project-Based-Folderwise-Data-Upload-API-for-Frappe

## Overview
This API allows users to upload various types of data, including images, labels, and model files, to the Frappe file system. It supports structured storage of data in a project-wise manner within the `Home/File` directory.

## Features
- Validates that the specified project exists in the system.
- Creates a structured, project-wise folder system for storing different types of data.
- Saves files securely in the Frappe private file system.
- Generates unique file names to prevent collisions.
- Associates files with the respective project for easy retrieval.

## API Endpoint
```python
@frappe.whitelist()
def upload_data(project_name, data_files, model_file=None)
```

## Request Parameters
| Parameter      | Type   | Description |
|---------------|--------|-------------|
| project_name  | str    | Name of the project to associate the data with. |
| data_files    | list   | A list of dictionaries containing file data and metadata (Images and Labels). |
| model_file    | dict   | (Optional) A dictionary containing the base64-encoded `.h5` model file data. |

### `data_files` Format
Each item in the `data_files` list should be a dictionary with the following keys:

```json
{
  "file_data": "<base64_encoded_file>",
  "file_name": "example.png",
  "category": "images" or "documents" or "others"
}
```

### `model_file` Format
If provided, `model_file` should be a dictionary with the following structure:


## Folder Structure
The API creates the following project-wise folder hierarchy:
```
Home/
 ├── File/
 │   ├── <project_name>/
 │   │   ├── images/ (for image files)
 │   │   ├── documents/ (for document files)
 │   │   ├── others/ (for other types of data)
 │   │   ├── model/ (for storing the .h5 model file)
```

## Error Handling
- If the project does not exist, the API throws an error.
- If file data or metadata is missing, an exception is raised.
- If saving the files fails, the system logs an error and rolls back changes.

## Notes
- Ensure that the user has appropriate permissions to create files in the Frappe file system.
- The function commits database changes after successful execution.
- Files are stored securely in the private file system for data protection.

## Usage
This API can be used for various purposes, including machine learning projects, document storage, and general data management within the Frappe framework.

