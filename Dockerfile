FROM python:3.7-alpine
RUN pip install requests
ADD statuspage.py statuspage.py
CMD ["python", "statuspage.py"]
