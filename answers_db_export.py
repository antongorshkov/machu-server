import mysql.connector

# Fill in your MySQL database connection details and SSL configuration
# TODO: Move to config: ${db.USERNAME}:${db.PASSWORD}@${db.HOSTNAME}:${db.PORT}/${db.DATABASE}
# TODO: in prod, certificate would be here: './ca_cert.cert'
db_config = {

}

# Establish the database connection with SSL CA certificate
connection = mysql.connector.connect(
    host=db_config["host"],
    user=db_config["user"],
    port=db_config["port"],
    password=db_config["password"],
    database=db_config["database"],
    ssl_ca=db_config["ssl_ca"]
)
cursor = connection.cursor()

# Execute the query to retrieve questions and their answers
query = """
SELECT 
    q.id, 
    q.title, 
    a.original_text
FROM 
    question q
JOIN 
    answer a ON q.id = a.question_id
ORDER BY 
    q.id;
"""
cursor.execute(query)
rows = cursor.fetchall()

# Process the data into a structured dictionary format
data = {}
for question_id, question_text, answer_text in rows:
    if question_id not in data:
        data[question_id] = {"question_text": question_text, "answers": []}
    data[question_id]["answers"].append(answer_text)

# Close the database connection
cursor.close()
connection.close()

# Format data for LLM input
formatted_data = [
    {
        "question": question_info["question_text"],
        "answers": question_info["answers"]
    }
    for question_info in data.values()
]

# Example: print the formatted data
for item in formatted_data:
    print("Question:", item["question"])
    print("Answers:", item["answers"])
    print("-" * 40)
