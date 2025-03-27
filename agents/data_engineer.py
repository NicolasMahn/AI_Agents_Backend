
from agent_util import do_basic_data_description
from agents.default_agent import Agent
from util import load_text


class DataEngineer(Agent):
    def __init__(self, project, is_clone=False):

        """
        I have removed this from teh role:

         ## **Key Responsibilities:**

            ### **1. Data Pipeline Setup**
            - Build and maintain **basic ETL pipelines** to collect and process data.
            - Ensure the AI agent has access to **structured data sources** like databases and APIs.
            - Handle **data storage** in a simple, efficient format (e.g., JSON, CSV, or SQL databases).

            ### **2. Data Cleaning & Processing**
            - Automate **data cleaning and validation** to remove errors and inconsistencies.
            - Transform raw data into a format the AI agent can easily use.
            - Support simple **feature extraction** for AI decision-making.

            ### **3. Performance & Maintenance**
            - Ensure **fast and reliable data access** for the AI agent.
            - Use **basic cloud storage** (e.g., AWS S3, Google Drive, or local databases) if needed.
            - Monitor and fix **data issues** to keep the system running smoothly.

            ### **4. Security & Compliance**
            - Follow **basic security best practices** (e.g., access controls, encryption).
            - Ensure compliance with **data privacy rules** (if handling user data).
            - Keep track of **data sources and updates** to maintain consistency.
        """

        if is_clone:
            role = """
            # **Role Description:**  
            You are a **Reviewer** of the **Data Engineer**. Your main responsibility is to control the Data Engineer 
            and escalate when necessary.
            The Data Engineers is responsible for setting up and maintain simple, efficient data pipelines that allow 
            the AI agent to access, process, and store data reliably. You ensure that the AI agent has clean, 
            structured data for basic tasks like retrieving information, processing inputs, and making simple decisions.

            Ensure that you always explain your thought process in detail and provide clear instructions to 
            the team members (to the data engineer).
                    """
            super().__init__(f"data_engineer_reviewer", role, project, is_clone=is_clone)
        else:
            role = """
            # **Role Description:**  
            You are a **Data Engineer**. Your main responsibility is to set up and maintain simple, efficient data 
            pipelines that allow the AI agent to access, process, and store data reliably. You ensure that the AI agent 
            has clean, structured data for basic tasks like retrieving information, processing inputs, and making 
            simple decisions.

            Ensure that you always explain your thought process in detail and provide clear instructions to 
            the team members (to your code reviewer).
                    """
            super().__init__(f"data_engineer", role, project, is_clone=is_clone)
        self.eligible_agents = ["product_owner", "data_scientist", "developer"]
        pass


    def create_data_description(self, uploaded_file_path):
        basic_data_description = do_basic_data_description(f"{self.project.get_project_dir()}/{uploaded_file_path}")
        file_name = uploaded_file_path.split("/")[-1].split(".")[0]
        self.data_description_file_path = f"{self.project.get_project_dir()}/data_description_{file_name}.txt"
        task = f"""
# **Task: Define Data Description**

A Datafile has been uploaded. You can find it here: `files/{ uploaded_file_path }`

A static method has already analyzed the data and provided a basic description: 
{basic_data_description}

You're job is it to refine the data description. 
For that you will probably need to write some code. You should find all document files (including the uploaded file) in the `files` directory.

Save the data description using the following format:
```xml
<data_description> Data Description here </data_description>
```

The data description can also be loaded from a file (txt, pkl, json, xml).
To do so you can use the following code:
```xml
<data_description load="file_path"> Add additional description here </data_description>
```

## **Data Description Guidelines:**
A data description should comprehensively explain the contents, structure, and characteristics of a dataset, 
making it easier for others to understand and use it. Here's what it should typically include:

**1. General Information**
* Dataset Name: A clear, descriptive title.
* File Format: CSV, JSON, XML, SQL, Parquet, etc.
* Size: Number of rows, columns, and total file size.
* Schema: A list of all fields/columns with descriptions.

**2. Field (Column) Descriptions**
* Column Name: The exact name of the field.
* Data Type: Numeric, text, categorical, date-time, boolean, etc.
* Units (if applicable): Currency, kilograms, seconds, etc.
* Meaning: What the field represents.
* Example Values: Sample data points.
* Missing Values: Explanation of null values or missing data treatment.

**4. Data Relationships**
* Primary Keys & Unique Identifiers: Which columns uniquely identify rows.
* Foreign Keys: Relationships to other datasets or tables.
* Hierarchies & Dependencies: Parent-child structures or aggregation levels.

5. Data Quality & Cleaning**
* Missing Data Handling: Imputed values, drop rules, or flagged missing entries.
* Duplicates: Whether duplicates exist and how they are handled.
* Errors & Outliers: How outliers are detected and treated.
* Data Normalization & Standardization: Any pre-processing applied.

**7. Data Usage & Applications**
* Limitations: Any known biases, restrictions, or constraints.
* Best Practices: Guidelines on how to analyze or interpret the data.

**8. Example Records**
* A small sample table showing typical values to illustrate data structure.

---

Ensure that you always explain your thought process in detail and provide clear instructions to the team members.
When you are done please print `<done />`
        """

        self.add_context_data("data_description", self.load_data_description,
                              "The data description of the current file", importance=2)


        test = f"""
# **Task: Control Data Description**
You are a Tester (Data Engineer B), tasked with verifying the data description created by the Data Engineer A.

The Data Engineer A has created a data description for the uploaded file: `files/{ uploaded_file_path }`

Your task for now ist to checkout the data and to create a list you believe to be important for the data description.
You will later review the data description created by the Data Engineer A.

You have to save your notes in your short_memory.


## **Data Description Guidelines:**
A data description should comprehensively explain the contents, structure, and characteristics of a dataset, 
making it easier for others to understand and use it. Here's what it should typically include:

**1. General Information**
* Dataset Name: A clear, descriptive title.
* File Format: CSV, JSON, XML, SQL, Parquet, etc.
* Size: Number of rows, columns, and total file size.
* Schema: A list of all fields/columns with descriptions.

**2. Field (Column) Descriptions**
* Column Name: The exact name of the field.
* Data Type: Numeric, text, categorical, date-time, boolean, etc.
* Units (if applicable): Currency, kilograms, seconds, etc.
* Meaning: What the field represents.
* Example Values: Sample data points.
* Missing Values: Explanation of null values or missing data treatment.

**4. Data Relationships**
* Primary Keys & Unique Identifiers: Which columns uniquely identify rows.
* Foreign Keys: Relationships to other datasets or tables.
* Hierarchies & Dependencies: Parent-child structures or aggregation levels.

5. Data Quality & Cleaning**
* Missing Data Handling: Imputed values, drop rules, or flagged missing entries.
* Duplicates: Whether duplicates exist and how they are handled.
* Errors & Outliers: How outliers are detected and treated.
* Data Normalization & Standardization: Any pre-processing applied.

**7. Data Usage & Applications**
* Limitations: Any known biases, restrictions, or constraints.
* Best Practices: Guidelines on how to analyze or interpret the data.

**8. Example Records**
* A small sample table showing typical values to illustrate data structure.

---

Ensure that you always explain your thought process in detail and provide clear instructions to the team members.
When you are done please print `<done />`
        """

        review_a = f"""
Explain your data description to the the tester, and refine it if necessary.

Save the data description using the following format:
```xml
<data_description> Data Description here </data_description>
```

Chat with the data engineer reviewer, by printing:
```xml
<chat agent="data_engineer_reviewer"> Your message here </chat>
```

The data description can also be loaded from a file (txt, pkl, json, xml).
To do so you can use the following code:
```xml
<data_description load="file_path"> Add additional description here </data_description>
```
        """

        review_b = f"""
The Data Engineer has created a data description for the uploaded file.

What do you think?

Please provide your feedback and suggestions for improvement.

Then relay those to the Data Engineer.

Chat with the data engineer, by printing:
```xml
<chat agent="data_engineer"> Your message here </chat>
```

Please do not hesitate to escalate if you believe that Data Engineer can not fix the problem.
Only he is entitle to directly edit his work!

When you believe the description is sufficient please print `<done />`
        """

        task_completion_requirements = ["code","data_description"]
        test_completion_requirements = ["code","short_memory"]
        review_a_completion_requirements = ["chat"]
        review_b_completion_requirements = ["chat"]

        self.do_task_with_test_and_review(task, test, review_a, review_b,
                                          task_completion_requirements, test_completion_requirements,
                                          review_a_completion_requirements, review_b_completion_requirements,
                                          "data_description", "data_description_review")

        self.project.add_data_description(self.data_description_file_path)

    def load_data_description(self):
        return load_text(self.data_description_file_path)

    def clone(self):
        return self.__class__(self.project, is_clone=True)

