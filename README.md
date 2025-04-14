# ImpactSpark

ImpactSpark is a scholarly impact analytics platform that provides insights into the reach and impact of academic research publications. It integrates data from various academic sources to help researchers and academics analyze the impact of their work.

## Features

- Search for academic publications by topic/keyword or DOI
- Advanced filtering options including:
  - Publication date ranges
  - Publication types
  - Open access filter
  - Citation count ranges
  - Research fields
  - Language filters
- Visual analytics and metrics about scholarly impact
- Integration with academic databases

## Prerequisites

- Docker installed on your system
- Git (for cloning the repository)

## Running with Docker

1. Clone the repository:
```bash
git clone https://github.com/aman-bcalm/ImpactSpark1.git
cd ImpactSpark1
```

2. Build the Docker image:
```bash
docker build -t impactspark .
```

3. Run the container:
```bash
docker run -p 8501:8501 impactspark
```

4. Access the application:
   - Open your web browser
   - Navigate to: `http://localhost:8501`

## Project Structure

- `impactspark.py` - Main application file
- `utils/` - Helper modules for API clients, data processing, and web scraping
- `requirements.txt` - Python dependencies
- `Dockerfile` - Docker configuration

## Note

When running the Docker container, make sure to use `http://localhost:8501` as the URL to access the application. The application will not be accessible through `0.0.0.0:8501` or other variations. 