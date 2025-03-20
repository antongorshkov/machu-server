# Machu Server API Documentation

This document provides information about the backend APIs used for managing directory entries, particularly focusing on adding, updating, and deleting contacts in the directory.

## Directory APIs

### GET `/directory`

Renders the directory page.

### GET `/get_directory_data`

Returns all directory entries from Airtable.

**Response Format:**
```json
{
  "records": [
    {
      "id": "recXXXXXXXXXXXXXX",
      "fields": {
        "Title": "Business Name",
        "Category": ["Category1", "Category2"],
        "Subtitle": "Business Description",
        "Phone Number": "+1234567890",
        "Website URL": "https://example.com",
        "Logo": [
          {
            "url": "https://example.com/logo.jpg",
            "filename": "logo.jpg"
          }
        ],
        "LogoCloudinaryUrl": "https://res.cloudinary.com/example/image/upload/logo.jpg"
      },
      "createdTime": "2023-01-01T00:00:00.000Z"
    }
  ]
}
```

### POST `/add_directory_entry`

Adds a new entry to the directory.

**Request Format:**

For JSON request:
```json
{
  "fields": {
    "Title": "Business Name",
    "Category": ["Category1"],
    "Subtitle": "Business Description",
    "Phone Number": "+1234567890",
    "Website URL": "https://example.com"
  }
}
```

For multipart/form-data request with logo upload:
- `data`: JSON string with the fields as shown above
- `logo_action`: Set to "upload" to upload a new logo
- `logo_file`: The image file to upload

**Important Notes:**
- `Title` and `Category` are required fields
- `Category` must be an array (even for a single category) as it maps to a Multiple Select field in Airtable
- Phone numbers should include the country code (e.g., "+1234567890")

**Response Format:**
```json
{
  "success": true,
  "data": {
    "id": "recXXXXXXXXXXXXXX",
    "fields": {
      "Title": "Business Name",
      "Category": ["Category1"],
      "Subtitle": "Business Description",
      "Phone Number": "+1234567890",
      "Website URL": "https://example.com",
      "Logo": [
        {
          "url": "https://example.com/logo.jpg",
          "filename": "logo.jpg"
        }
      ]
    }
  }
}
```

### POST `/update_directory_entry`

Updates an existing directory entry.

**Request Format:**

For JSON request:
```json
{
  "record_id": "recXXXXXXXXXXXXXX",
  "fields": {
    "Title": "Updated Business Name",
    "Category": ["Category1", "Category2"],
    "Subtitle": "Updated Business Description",
    "Phone Number": "+1234567890",
    "Website URL": "https://example.com"
  }
}
```

For multipart/form-data request with logo handling:
- `data`: JSON string with the record_id and fields as shown above
- `logo_action`: 
  - "keep" to keep the existing logo (default)
  - "upload" to upload a new logo
  - "remove" to remove the existing logo
- `logo_file`: The image file to upload (only if logo_action is "upload")

**Important Notes:**
- `record_id` is required and must correspond to an existing Airtable record
- `Title` and `Category` are required fields
- `Category` must be an array (even for a single category) as it maps to a Multiple Select field in Airtable
- All fields that are included will be updated; omitted fields remain unchanged

**Response Format:**
```json
{
  "success": true,
  "message": "Record updated successfully",
  "record": {
    "id": "recXXXXXXXXXXXXXX",
    "fields": {
      "Title": "Updated Business Name",
      "Category": ["Category1", "Category2"],
      "Subtitle": "Updated Business Description",
      "Phone Number": "+1234567890",
      "Website URL": "https://example.com",
      "Logo": [
        {
          "url": "https://example.com/logo.jpg",
          "filename": "logo.jpg"
        }
      ],
      "LogoCloudinaryUrl": "https://res.cloudinary.com/example/image/upload/logo.jpg"
    }
  },
  "id": "recXXXXXXXXXXXXXX",
  "logoUrl": "https://example.com/logo.jpg"
}
```

### POST `/delete_directory_entry`

Deletes an existing directory entry.

**Request Format:**
```json
{
  "record_id": "recXXXXXXXXXXXXXX"
}
```

**Important Notes:**
- `record_id` is required and must correspond to an existing Airtable record
- This operation is permanent and cannot be undone

**Response Format:**
```json
{
  "success": true,
  "message": "Record deleted successfully"
}
```

## Error Responses

All APIs follow the same error response format:

```json
{
  "success": false,
  "error": "Error message describing what went wrong"
}
```

Common error scenarios:
- Missing required fields
- Invalid record ID
- Airtable API errors
- Authorization errors (missing or invalid API keys)

## Environment Variables

The following environment variables are used by these APIs:
- `AIRTABLE_API_KEY` or `AIRTABLE_TOKEN`: Your Airtable API key
- `AIRTABLE_BASE_ID`: The ID of your Airtable base (default: "appU0yK4n5WOdzSDU")
- `AIRTABLE_TABLE_NAME`: The name of your Airtable table (default: "main-directory")
- `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`: If using Cloudinary for logo storage
