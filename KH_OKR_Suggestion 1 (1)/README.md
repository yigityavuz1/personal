# Koç Holding OKR Suggestion Project

## Project Overview
The Koç Holding OKR Suggestion project is designed to facilitate the improvement of objectives and key results (OKRs) through a FastAPI application running inside a Docker container. Additionally, the project includes several chatbots for different purposes.

## Endpoints

### Objective Endpoints
1. **Improve Objectives**
   - **Endpoint:** `/improve_objective`
   - **Method:** POST
   - **Request Model:**
     ```python
     class ObjectiveRequestModel(BaseModel):
         SessionID: str
         UserID: str
         ObjectiveID: str
         Objective: str
     ```
   - **Response Model:**
     ```python
     class ObjectiveResponseModel(BaseModel):
         SessionID: str
         UserID: str
         ObjectiveID: str
         NewObjectives: str = None
     ```

2. **Improve Key Results**
   - **Endpoint:** `/improve_key_result`
   - **Method:** POST
   - **Request Model:**
     ```python
     class KeyResultRequestModel(BaseModel):
         SessionID: str
         UserID: str
         KeyResultID: str
         KeyResult: str
     ```
   - **Response Model:**
     ```python
     class KeyResultResponseModel(BaseModel):
         SessionID: str
         UserID: str
         KeyResultID: str
         NewKeyResult: str = None
     ```

### Chatbot Endpoints
1. **User Chats**
   - **Endpoints:** `/okr_chat`, `/okr_suggestion_chat`, `/development_kr_suggestion_chat`, `/aligned_okr_suggestion_chat`
   - **Method:** POST
   - **Request Model:**
     ```python
     class ChatRequestModel(BaseModel):
         SessionID: str
         UserID: str
         UserName: str
         CompanyName: str
         CompanyGroup: str
         Department: str
         Position: str
         HireDate: str
         UserMessage: str
         ChatHistory: list
     ```
   - **Response Model:**
     ```python
     class ChatResponseModel(BaseModel):
         SessionID: str
         UserID: str
         LLMAnswer: str = None
     ```

## Usage

### Running the FastAPI Application in Docker
1. Build the Docker image:
   ```bash
   docker build -t koc-holding-okr .
   ```

2. Run the Docker container:
   ```bash
   docker run -p 8000:8000 koc-holding-okr
   ```

3. Run the `sample_request.py` for testing the endpoints:
 ```bash
   python sample_request.py
   ```
Or, access the FastAPI documentation at http://localhost:8000/docs for detailed API information and testing.

### For Local Testing 
1. Navigate to the `src` folder:

   ```bash
   cd src
   ```

3. Build and run the Docker container:

   ```bash
   docker-compose up --build
   ```

   This command will build the Docker image and start the FastAPI application.