# Use the official Python image as the base image
FROM python:3.8

# Set the working directory in the container
WORKDIR /app

# Copy requirements file and install dependencies
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application files into the working directory
COPY . .


EXPOSE 8000

# Define the entry point for the container
#CMD ["gunicorn", "--bind", "0.0.0.0:8000", "stock_data.wsgi"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8080"]


