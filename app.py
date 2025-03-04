import frappe
import json
import base64
import os

@frappe.whitelist()
def upload_training_data(project_name, training_data, model_file=None):
    """Uploads training data (images and labels) to the Frappe file system.
    Also allows uploading a trained model file in .h5 format.
    
    Args:
        project_name (str): The name of the project to associate the training data with.
        training_data (list): A list of dictionaries, where each dictionary contains:
            - image (str): The base64 encoded image data.
            - label (str): The label for the image ('ok' or 'defective').
        model_file (dict, optional): Dictionary containing:
            - file_data (str): The base64 encoded model file data (.h5 format).
            - file_name (str): The name of the model file.
    """
    try:
        training_data = json.loads(training_data) if isinstance(training_data, str) else training_data
        model_file = json.loads(model_file) if isinstance(model_file, str) and model_file else model_file
        
        # Validate that project exists
        if not frappe.db.exists("Project", project_name):
            frappe.throw(f"Project '{project_name}' does not exist.")
        
        # Function to create folder and return the folder document
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
        
        # Create folder structure (training_data/project_name/[ok, defective, model])
        training_data_folder = create_folder("training_data")
        project_folder = create_folder(project_name, training_data_folder.name)
        ok_folder = create_folder("ok", project_folder.name)
        defective_folder = create_folder("defective", project_folder.name)
        model_folder = create_folder("model", project_folder.name)
        
        # Create physical directories
        site_path = frappe.get_site_path()
        private_files_path = os.path.join(site_path, "private", "files")
        
        # Create full physical paths matching Frappe's folder structure
        base_path = os.path.join(private_files_path, "Home")
        training_data_path = os.path.join(base_path, "training_data")
        project_path = os.path.join(training_data_path, project_name)
        ok_path = os.path.join(project_path, "ok")
        defective_path = os.path.join(project_path, "defective")
        model_path = os.path.join(project_path, "model")
        
        # Create physical directories if they don't exist
        os.makedirs(training_data_path, exist_ok=True)
        os.makedirs(project_path, exist_ok=True)
        os.makedirs(ok_path, exist_ok=True)
        os.makedirs(defective_path, exist_ok=True)
        os.makedirs(model_path, exist_ok=True)
        
        uploaded_files = []
        
        # Process training data images
        for idx, data in enumerate(training_data):
            label = data.get("label", "").lower()
            image_data = data.get("image")
            
            if not image_data or not label:
                frappe.throw("Invalid training data format: Missing image or label.")
                
            # Determine parent folder and path based on label
            if label == "ok":
                parent_folder = ok_folder
                folder_path = ok_path
            elif label == "defective":
                parent_folder = defective_folder
                folder_path = defective_path
            else:
                continue  # Skip any label that's not 'ok' or 'defective' for images
                
            # Generate a unique file name with index to avoid collisions
            file_name = f"{project_name}{label}{idx+1}_{frappe.generate_hash(length=6)}.png"
            file_path = os.path.join(folder_path, file_name)
            
            # Decode base64 image data and save to file system
            try:
                # Remove potential data URL prefix
                if "," in image_data:
                    image_data = image_data.split(",")[1]
                    
                with open(file_path, "wb") as f:
                    f.write(base64.b64decode(image_data))
            except Exception as e:
                frappe.throw(f"Error saving image file: {str(e)}")
                
            # Create File document to make it visible in File Manager
            file_doc = frappe.new_doc("File")
            file_doc.file_name = file_name
            file_doc.is_private = 1
            file_doc.folder = parent_folder.name
            
            # Important: Link file to the project document type
            file_doc.attached_to_doctype = "Project"
            file_doc.attached_to_name = project_name
            
            file_doc.file_size = os.path.getsize(file_path)
            file_doc.content_hash = frappe.generate_hash(length=10)
            
            # Set the correct file URL
            relative_url = f"private/files/Home/training_data/{project_name}/{label}/{file_name}"
            file_doc.file_url = f"/{relative_url}"
            
            file_doc.insert(ignore_permissions=True)
            
            # Save record in the database
            # doc = frappe.new_doc("metalcasttrain")
            # doc.project = project_name
            # doc.image = file_doc.file_url
            # doc.label = label
            # doc.insert(ignore_permissions=True)
            
            uploaded_files.append({
                "name": file_name,
                "url": file_doc.file_url,
                "label": label,
                "docname": file_doc.name
            })
        
        # Process model file if provided
        model_file_info = None
        if model_file and model_file.get("file_data") and model_file.get("file_name"):
            file_data = model_file.get("file_data")
            original_file_name = model_file.get("file_name")
            
            # Ensure the file has .h5 extension
            file_name_parts = os.path.splitext(original_file_name)
            base_name = file_name_parts[0]
            extension = file_name_parts[1].lower() if len(file_name_parts) > 1 else ""
            
            if extension != ".h5":
                # Force .h5 extension if not provided
                extension = ".h5"
                
            # Generate a unique model file name with .h5 extension
            model_file_name = f"{project_name}model{frappe.generate_hash(length=8)}{extension}"
            model_file_path = os.path.join(model_path, model_file_name)
            
            # Decode base64 model data and save to file system
            try:
                # Remove potential data URL prefix
                if "," in file_data:
                    file_data = file_data.split(",")[1]
                    
                with open(model_file_path, "wb") as f:
                    f.write(base64.b64decode(file_data))
            except Exception as e:
                frappe.throw(f"Error saving model file: {str(e)}")
                
            # Create File document for the model
            file_doc = frappe.new_doc("File")
            file_doc.file_name = model_file_name
            file_doc.is_private = 1
            file_doc.folder = model_folder.name
            
            # Link file to the project
            file_doc.attached_to_doctype = "Project"
            file_doc.attached_to_name = project_name
            
            file_doc.file_size = os.path.getsize(model_file_path)
            file_doc.content_hash = frappe.generate_hash(length=10)
            
            # Set the correct file URL
            relative_url = f"private/files/Home/training_data/{project_name}/model/{model_file_name}"
            file_doc.file_url = f"/{relative_url}"
            
            file_doc.insert(ignore_permissions=True)
            
            # Save model record in the database (using same metalcasttrain table with special label)
            # doc = frappe.new_doc("metalcasttrain")
            # doc.project = project_name
            # doc.image = file_doc.file_url
            # doc.label = "model"  # Special label for model files
            # doc.insert(ignore_permissions=True)
            
            model_file_info = {
                "name": model_file_name,
                "original_name": original_file_name,
                "url": file_doc.file_url,
                "docname": file_doc.name
            }
            
            # Add to uploaded files list
            uploaded_files.append({
                "name": model_file_name,
                "url": file_doc.file_url,
                "label": "model",
                "docname": file_doc.name
            })
            
        frappe.db.commit()
        
        # Prepare message based on what was uploaded
        upload_message = "Training data"
        if model_file_info:
            upload_message += " and model file (.h5)"
        upload_message += " uploaded successfully. Please refresh the file manager to see all files."
        
        frappe.msgprint(upload_message)
        
        response = {
            "message": upload_message,
            "files": uploaded_files,
            "project": project_name,
            "count": len(uploaded_files),
            "folder_path": f"/app/file/Home/training_data/{project_name}"
        }
        
        # Add model info if available
        if model_file_info:
            response["model_file"] = model_file_info
            
        return response
        
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(title="Error uploading training data or model", message=frappe.get_traceback())
        frappe.throw(f"Failed to upload training data or model: {str(e)}")