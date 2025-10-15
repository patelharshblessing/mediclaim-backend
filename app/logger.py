import logging

# Configure the logger
logging.basicConfig(
    level=logging.INFO,  # Default level
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("app.log"),  # Log to a file
        logging.StreamHandler(),  # Log to the console
    ],
)


# Create a logger instance
def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
