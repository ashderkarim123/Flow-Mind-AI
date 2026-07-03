## **FlowMind AI** 

**Ashder Karim (2280137) Adnan Didar (2280229) Zohaib Iqbal (2280169)** 

## **Supervised by: Mr. Ammad Noor** 

**In partial fulfillment of requirement for the degree Bachelor of Science (Software Engineering) Shaheed Zulfikar Ali Bhutto Institute of Science and Technology Islamabad, Pakistan** 

**April, 2026** 

## **FlowMind AI** 

## _**By**_ 

## _**Ashder Karim, Adnan Didar, Zohaib Iqbal**_ **CERTIFICATE** 

## **A THESIS SUBMITTED IN PARTIAL FULFILLMENT OF THE REQUIREMENTS FOR THE DEGREE OF BACHELOR OF SCIENCE IN SOFTWARE ENGINEERING (BSSE).** 

**It is to certify that the above students thesis has been completed to my satisfaction and, to my belief, its standard is appropriate for submission for Evaluation. I have also conducted plagiarism test of this thesis using HEC prescribed software and found similarity index “write plagiarism percentage” that is within the permissible limit set by the HEC for the BSSE degree thesis. I have also found the thesis in a format recognized by SZABIST for the BSSE thesis.** 

(Supervisor) (Project Coordinator) Ammad Noor Fakhar ul Islam 

(BSSE Program Manager) Sheikh Abdul Wahab 

Date: 

**Department of Computer Science, Shaheed Zulfikar Ali Bhutto Institute of Science and Technology, Islamabad Campus** 

**April, 2026** 

## **Project Overview** 

FlowMind AI is an intelligent web-based no-code workflow automation platform designed to simplify the creation, execution, and management of artificial intelligence-driven workflows. The platform addresses the gap between advanced AI technologies and nontechnical users by providing a visual environment where users can design automated processes without writing code. Through a drag-and-drop workflow builder, users can connect different functional nodes, configure AI prompts, integrate external services, and execute workflows in an organized and user-friendly manner. 

The system integrates Firebase Authentication, Firebase Firestore, a Next.js and React frontend, and a Python FastAPI backend. Firebase Authentication manages secure user registration, login, and session handling, while Firestore stores user profiles, workflow definitions, nodes, edges, execution records, analytics, notifications, templates, and other application data. The backend exposes REST APIs for authentication verification, workflow management, analytics, integrations, templates, marketplace-related operations, billing, notifications, audit logs, and admin functions. The workflow canvas is implemented using a node-based interface that enables users to visually construct AI-powered automation flows. 

FlowMind AI supports integration with multiple AI providers such as OpenAI, Gemini, Claude, and other compatible model APIs. This multi-model approach allows users to select suitable models for different tasks such as content generation, data processing, decision support, and automated reasoning. The system also includes separate access flows for normal users and administrators. Normal users can create workflows, execute them, view outputs, and monitor analytics, while administrators can manage users, review platform activity, monitor workflows, and access system-level information. 

The documentation follows the SZABIST official final year project structure and includes an introduction, software requirements specification, software project plan, functional analysis and modeling, and system design. The project contributes to the democratization of AI automation by providing an accessible, affordable, and scalable platform for students, freelancers, startups, small businesses, and enterprises seeking to automate repetitive tasks and improve productivity through AI-enabled workflows. 

ii 

## **Dedication** 

First and foremost, we dedicate this project to Allah Almighty, whose countless blessings, guidance, and mercy made this work possible. We also dedicate this work to the Holy Prophet Muhammad (Peace Be Upon Him), whose teachings continue to guide humanity toward knowledge, patience, discipline, and service. 

We dedicate this project to our beloved parents, whose prayers, sacrifices, encouragement, and unconditional support have been the foundation of our academic journey. Their constant motivation gave us the strength to complete this project with dedication and commitment. 

We also dedicate this work to our respected teachers, supervisor, friends, and all those who supported us throughout the development of FlowMind AI. Their guidance, feedback, and encouragement played an important role in shaping this project. 

iii 

## **Acknowledgement** 

The requirements for the degree of Bachelor of Software Engineering. 

Ashder Karim Zohaib Iqbal 2280137 2280169 Adnan Didar 2280229 

iv 

## **Revision History** 

|**Compiled By**|**Checked By**|**Date**|**Description of Change**|**Ver.**|
|---|---|---|---|---|
|Ashder Karim|Mr. Ammad Noor|26-Feb-2026|Project kickof; initial requirements<br>elicitation and stakeholder analysis<br>completed.|1.0|
|Adnan Didar|Mr. Ammad Noor|05-Mar-2026|Refnement of functional and<br>non-functional requirements based<br>on feedback.|1.1|
|Zohaib Iqbal|Mr. Ammad Noor|12-Mar-2026|Software Requirements Specifcation<br>(SRS) reviewed and fnalized.|1.2|
|Ashder Karim|Mr. Ammad Noor|20-Mar-2026|Agile methodology adopted; sprint<br>planning and backlog structuring<br>completed.|1.3|
|Adnan Didar|Mr. Ammad Noor|26-Mar-2026|Use case diagrams validated and<br>updated for consistency.|1.4|
|Zohaib Iqbal|Mr. Ammad Noor|02-Apr-2026|Database design improved; ER<br>diagrams and schema normalized.|1.5|
|Ashder Karim|Mr. Ammad Noor|09-Apr-2026|System architecture fnalized; API<br>contracts defned.|1.6|
|Adnan Didar|Mr. Ammad Noor|16-Apr-2026|UI/UX wireframes and workfow<br>canvas refned for usability<br>improvements.|1.7|
|Zohaib Iqbal|Mr. Ammad Noor|23-Apr-2026|Authentication module and<br>role-based access control<br>enhancements added.|1.8|
|Ashder Karim|Mr. Ammad Noor|30-Apr-2026|Workfow builder engine<br>functionality improved and<br>stabilized.|1.9|
|Adnan Didar|Mr. Ammad Noor|07-May-2026|Multi-model AI integration<br>implemented across core system<br>modules.|2.0|
|Zohaib Iqbal|Mr. Ammad Noor|14-May-2026|Comparative AI response evaluation<br>feature refned and optimized.|2.1|
|Ashder Karim|Mr. Ammad Noor|21-May-2026|Test planning completed;<br>module-level verifcation initiated.|2.2|
|Adnan Didar|Mr. Ammad Noor|28-May-2026|System testing conducted; bug fxes<br>and stability improvements applied.|2.3|
|Zohaib Iqbal|Mr. Ammad Noor|04-Jun-2026|Documentation chapters reviewed<br>and improved for fnal submission.|2.4|
|Ashder Karim|Mr. Ammad Noor|11-Jun-2026|Risk analysis updated; future<br>enhancement roadmap documented.|2.5|
|Adnan Didar|Mr. Ammad Noor|18-Jun-2026|Final progress review completed;<br>supervisor approval obtained.|2.6|



## **Contents** 

|**Project Overview**|**Project Overview**|**Project Overview**|||**ii**|
|---|---|---|---|---|---|
|**Dedication**|||||**iii**|
|**Acknowledgements**|||||**iv**|
|**List of **||**Figures**|||**iii**|
|**List of **||**Tables**|||**iv**|
|**1**|**Introduction**||||**v**|
||1.1|Product Purpose<br>. . . . . . . . .|. . . . . .|. . . . . . . . . . . . . . . .|v|
||1.2|Product Scope . . . . . . . . . . .|. . . . . .|. . . . . . . . . . . . . . . .|1|
|||1.2.1<br>Existing System Description . . . . .||. . . . . . . . . . . . . . . .|2|
|||1.2.2<br>Future System Usage Analysis . . . .||. . . . . . . . . . . . . . . .|3|
||1.3|Objectives . . . . . . . . . . . . .|. . . . . .|. . . . . . . . . . . . . . . .|4|
||1.4|Problem Statement / Limitations|. . . . . .|. . . . . . . . . . . . . . . .|4|
||1.5|Proposed Solution . . . . . . . . .|. . . . . .|. . . . . . . . . . . . . . . .|5|
||1.6|Intended Market of Product . . .|. . . . . .|. . . . . . . . . . . . . . . .|6|
||1.7|Intended Users of Product . . . .|. . . . . .|. . . . . . . . . . . . . . . .|6|
||1.8|Software Process Model<br>. . . . .|. . . . . .|. . . . . . . . . . . . . . . .|7|
|||1.8.1<br>Process Model Introduction|. . . . .|. . . . . . . . . . . . . . . .|7|
|||1.8.2<br>Justifcation of Proposing the process model . . . . . . . . . . . .|||7|
|||1.8.3<br>Steps of Process Model . .|. . . . . .|. . . . . . . . . . . . . . . .|7|
|**2**|**SOFTWARE REQUIREMENTS SPECIFICATION**||||**9**|
||2.1|Introduction . . . . . . . . . . . .|. . . . . .|. . . . . . . . . . . . . . . .|9|
|||2.1.1<br>Document Scope<br>. . . . .|. . . . . .|. . . . . . . . . . . . . . . .|9|
|||2.1.2<br>Audience . . . . . . . . . .|. . . . . .|. . . . . . . . . . . . . . . .|9|
||2.2|Functional Requirements . . . . .|. . . . . .|. . . . . . . . . . . . . . . .|9|
||2.3|Non-Functional Requirements . .|. . . . . .|. . . . . . . . . . . . . . . .|10|
|||2.3.1<br>Software Quality Attributes . . . . .||. . . . . . . . . . . . . . . .|11|
|||2.3.2<br>Other Non-Functional Requirements||. . . . . . . . . . . . . . . .|11|
||2.4|Requirement Gathering Techniques Used . .||. . . . . . . . . . . . . . . .|11|
|||2.4.1<br>Focus Group . . . . . . . .|. . . . . .|. . . . . . . . . . . . . . . .|11|
|||2.4.2<br>User Observation . . . . .|. . . . . .|. . . . . . . . . . . . . . . .|11|
|||2.4.3<br>Analyze Existing Systems|. . . . . .|. . . . . . . . . . . . . . . .|12|
||2.5|Time Frame . . . . . . . . . . . .|. . . . . .|. . . . . . . . . . . . . . . .|12|
|**3**|**SOFTWARE PROJECT PLAN**||||**13**|
||3.1|Deliverables of the Project . . . .|. . . . . .|. . . . . . . . . . . . . . . .|13|
||3.2|Software Project Management Plan . . . . .||. . . . . . . . . . . . . . . .|13|
|||3.2.1<br>Project Planning . . . . .|. . . . . .|. . . . . . . . . . . . . . . .|13|
|||3.2.2<br>Project Scheduling . . . .|. . . . . .|. . . . . . . . . . . . . . . .|14|
||3.3|Managerial Process . . . . . . . .|. . . . . .|. . . . . . . . . . . . . . . .|15|
|||3.3.1<br>Management Objectives and Priorities||. . . . . . . . . . . . . . .|15|



i 

|||3.3.2<br>Assumptions and Constraints|. . . . . . . . . . . . . . . . . . . .|15|
|---|---|---|---|---|
||3.4|Project Risk Management . . . . .|. . . . . . . . . . . . . . . . . . . . .|16|
|||3.4.1<br>Risk Management Plan . . .|. . . . . . . . . . . . . . . . . . . . .|16|
|||3.4.2<br>Risk Management Activities|. . . . . . . . . . . . . . . . . . . . .|16|
|**4**|**FUNCTIONAL ANALYSIS AND MODELING**|||**18**|
||4.1|Use Case Modeling . . . . . . . . .|. . . . . . . . . . . . . . . . . . . . .|18|
|||4.1.1<br>User Stories . . . . . . . . .|. . . . . . . . . . . . . . . . . . . . .|19|
|||4.1.2<br>Individual Actor Use Cases|. . . . . . . . . . . . . . . . . . . . .|20|
||4.2|Functional Modeling<br>. . . . . . . .|. . . . . . . . . . . . . . . . . . . . .|22|
|||4.2.1<br>Entity Relationship Diagram|. . . . . . . . . . . . . . . . . . . . .|22|
|||4.2.2<br>Data Flow Diagram . . . . .|. . . . . . . . . . . . . . . . . . . . .|23|
|**5**|**SYSTEM DESIGN**|||**26**|
||5.1|Structure Diagrams . . . . . . . . .|. . . . . . . . . . . . . . . . . . . . .|26|
|||5.1.1<br>Class Diagram . . . . . . . .|. . . . . . . . . . . . . . . . . . . . .|26|
|||5.1.2<br>Deployment Diagrams<br>. . .|. . . . . . . . . . . . . . . . . . . . .|26|
||5.2|Behavioral Diagrams . . . . . . . .|. . . . . . . . . . . . . . . . . . . . .|27|
|||5.2.1<br>Activity Diagrams<br>. . . . .|. . . . . . . . . . . . . . . . . . . . .|27|
|||5.2.2<br>Communication Diagrams .|. . . . . . . . . . . . . . . . . . . . .|28|
|||5.2.3<br>Sequence Diagrams . . . . .|. . . . . . . . . . . . . . . . . . . . .|29|
||5.3|System Architecture Diagram . . .|. . . . . . . . . . . . . . . . . . . . .|34|
||5.4|Component Diagram . . . . . . . .|. . . . . . . . . . . . . . . . . . . . .|35|
||5.5|Conclusion . . . . . . . . . . . . . .|. . . . . . . . . . . . . . . . . . . . .|35|



## **List of Figures** 

|1.1|Agile Scrum Framework<br>. . . . . . . . . . . . . . . . . . . . . . . . . . .|7|
|---|---|---|
|3.1|Gantt Chart . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .|14|
|3.2|Work Break Down Structure . . . . . . . . . . . . . . . . . . . . . . . . .|15|
|3.3|Critical Path<br>. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .|15|
|4.1|Use case Diagram . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .|18|
|4.2|ERD Diagram . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .|23|
|4.3|DFD Level 0 Diagram<br>. . . . . . . . . . . . . . . . . . . . . . . . . . . .|24|
|4.4|DFD Level 1 Diagram<br>. . . . . . . . . . . . . . . . . . . . . . . . . . . .|24|
|4.5|DFD Level 2 Diagram<br>. . . . . . . . . . . . . . . . . . . . . . . . . . . .|24|
|5.1|Class Diagram . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .|26|
|5.2|Deployment . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .|27|
|5.3|Activity Diagram . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .|28|
|5.4|Communication Diagram . . . . . . . . . . . . . . . . . . . . . . . . . . .|29|
|5.5|Sequence Diagram for Register User . . . . . . . . . . . . . . . . . . . . .|29|
|5.6|Sequence Diagram for Authenticate User . . . . . . . . . . . . . . . . . .|30|
|5.7|Sequence Diagram for Create Workfow . . . . . . . . . . . . . . . . . . .|31|
|5.8|Sequence Diagram for Execute Workfow . . . . . . . . . . . . . . . . . .|32|
|5.9|Sequence Diagram for View Analytics . . . . . . . . . . . . . . . . . . . .|33|
|5.10|Sequence Diagram for Admin Management . . . . . . . . . . . . . . . . .|34|
|5.11|System Architecture of FlowMind AI . . . . . . . . . . . . . . . . . . . .|34|
|5.12|Component Diagram of FlowMind AI . . . . . . . . . . . . . . . . . . . .|35|



iii 

## **List of Tables** 

|1.1|Abbreviations . . . . . . . . . . . . .|. . . . . . . . . . . . . . . . . . . .|2|
|---|---|---|---|
|1.2|Applications Comparison . . . . . . .|. . . . . . . . . . . . . . . . . . . .|3|
|2.1|Functional Requirements of FlowMind|AI . . . . . . . . . . . . . . . . . .|10|
|2.2|Project Time Frame<br>. . . . . . . . .|. . . . . . . . . . . . . . . . . . . .|12|
|3.1|Risk Identifcation Table . . . . . . .|. . . . . . . . . . . . . . . . . . . .|16|
|3.2|Risk and Mitigation Strategies . . . .|. . . . . . . . . . . . . . . . . . . .|17|
|4.1|User Stories of FlowMind AI . . . . .|. . . . . . . . . . . . . . . . . . . .|19|
|4.2|Use Case Table of Register User . . .|. . . . . . . . . . . . . . . . . . . .|20|
|4.3|Use Case Table of Authenticate User|. . . . . . . . . . . . . . . . . . . .|20|
|4.4|Use Case Table of Create Workfow .|. . . . . . . . . . . . . . . . . . . .|20|
|4.5|Use Case Table of Confgure AI Nodes|. . . . . . . . . . . . . . . . . . .|21|
|4.6|Use Case Table of Execute Workfow|. . . . . . . . . . . . . . . . . . . .|21|
|4.7|Use Case Table of View Analytics . .|. . . . . . . . . . . . . . . . . . . .|21|
|4.8|Use Case Table of Manage Templates|. . . . . . . . . . . . . . . . . . . .|22|
|4.9|Use Case Table of Manage Integrations . . . . . . . . . . . . . . . . . . .||22|
|4.10|Use Case Table of Admin Dashboard|. . . . . . . . . . . . . . . . . . . .|22|



iv 

## **Chapter 1** 

## **Introduction** 

Artificial Intelligence has become an important part of modern software systems, business operations, education, digital marketing, customer support, data analysis, and enterprise automation. Organizations increasingly use AI tools to generate content, analyze information, automate repetitive activities, and support decision-making. However, despite the rapid progress of AI, the practical use of custom AI workflows is still difficult for many non-technical users. Building AI agents or automated workflows normally requires programming knowledge, API configuration, model selection, deployment skills, and understanding of integration logic. 

Existing automation platforms such as n8n, Make.com, and Zapier provide useful workflow automation features, but many of them are either technical in nature, expensive for advanced usage, or limited in AI-specific orchestration. Most platforms provide general trigger-action automation but do not fully focus on multi-model AI workflows, comparative AI responses, accessible workflow design, and transparent execution monitoring. As a result, students, freelancers, startups, small businesses, and non-technical users face barriers when trying to use AI automation in their daily tasks. 

FlowMind AI is proposed as a web-based no-code workflow automation platform that enables users to create, manage, execute, and monitor AI-driven workflows through a visual drag-and-drop interface. The system uses a node-based workflow canvas where users can add functional nodes, configure prompts, connect nodes, and execute workflows without writing code. The system integrates multiple AI providers such as OpenAI, Gemini, Claude, and other compatible model APIs to support flexible AI-powered automation. 

In this project, we will be using Next.js and React as our front end technologies, and Firebase Authentication as our authentication. for secure user login, Firebase Firestore for data storage and Python FastAPI for the web application. In the backend, for REST APIs. It includes normal user and admin access stream. Normal users can develop workflows, run them, manage templates, view analytics, and obtain workflows that will be sent to them. Administrators can manage users, monitor workflows, and review analytics, among other things, by means of notifications. and manage and control system operations. This renders FlowMind AI a sensible and scalable solution. Easy to access AI workflow automation solution. 

## **1.1 Product Purpose** 

The goal of FlowMind AI is to make creating and utilizing AI-driven tools easier. Nontechnical workflows for those who aren’t that technical or haven’t had much programming experience. The system seeks to bring Artificial Intelligence to the masses by enabling users to use the system in a visual manner. Automate processes in design with a dragand-drop approach, rather than coding. Or manually setting up complex API pipelines. The project tackles a key aspect that is missing from the existing workflow automation tools: The disparity between the capabilities of AI and accessibility for users. Many of 

v 

_CHAPTER 1. INTRODUCTION_ 

1 

the users are aware of the significance of it. Although AI can perform almost anything, it’s difficult to design custom workflows that involve prompts, AI models and API. 

Data calls, data transformation and generation of output. The FlowMind AI is a framework for These steps are represented as nodes which can be connected on a configured. Additionally, it will be built to support multiple models for the use of AI. Rather than relying on, With only one AI provider, the system can connect with other AI providers such as OpenAI, Gemini. and Claude. This allows the users to choose models according to the need of the task, The quality of response, the response cost and performance. Lastly, it helps to achieve the project objective of intelligent AI orchestration. The AI project platform that we are currently planning features core support for invoking multiple AI models. It discards the traditional model of binding users to a single service provider, and supports integration with mainstream large models including OpenAI, Gemini, and Claude. Users can independently select models based on four core criteria, which include task requirements, to ultimately achieve the core goal of this project: intelligent AI orchestration. 

## **1.2 Product Scope** 

Product scope is the scope, features, goals and constraints of the product. FlowMind AI. It outlines important aspects of the primary system to be realized and Explains how the platform will be utilised by its target user. The list of FlowMind AI capabilities is limited to: Enforce authentication, create visual workflow, store workflows, integrate an AI model, All of the workflows are included.The package contains workflow execution, workflow analytics, workflow admin management, workflow templates, workflow notifications and external workflows. integrations. The system is designed to be a web application and is used via the latest modern browsers. browsers. The front end is built with Next.js and React and the authentication is implemented with Firebase Authentication. Authenticates with and stores data in the cloud using and Firebase Firestore. The backend is written in Python FastAPI, and offers REST APIs for authentication. The verification, workflow management, analytics, integrations, billing and templates features are also included. Marketplace activities related to the market, notifications and administration. 

_CHAPTER 1. INTRODUCTION_ 

2 

Table 1.1: Abbreviations 

|**Serial**<br>**#**|**Abbreviation**|**Defnition**|
|---|---|---|
|1|AI|Artifcial Intelligence|
|2|API|Application Programming Interface|
|3|LLM|Large Language Model|
|4|UI|User Interface|
|5|UX|User Experience|
|6|DB|Database|
|7|RBAC|Role-Based Access Control|
|8|SRS|Software Requirements Specifcation|
|9|REST|Representational State Transfer|
|10|SaaS|Software as a Service|
|11|DFD|Data Flow Diagram|
|12|ERD|Entity Relationship Diagram|



The basic scope of the platform consists of the following modules: 

- Firebase-based user authentication and session handling. 

- User profile management and role access for normal users and administrator. 

- Visual workflow builder using a node-based drag-and-drop canvas. , updating, deletion, saving and retrieval of workflows. 

- AI node configuration and integration with OpenAI, Gemini, Claude and other model APIs. 

- Running workflows and creating outputs. 

- Analytics and monitoring of workflow execution history, response time, usage and errors. 

- Management of reusable workflow structures: Template. 

- Notification management for system and workflow notifications. 

- Admin panel to monitor and manage the platform. 

- API and integration module for third-party service connections and webhooks. 

## **1.2.1 Existing System Description** 

There are a few already available workflow automation tools in the market. The most The main competitors are n8n, Make.com and Zapier. These systems allow users need to connect applications and automate tasks, they have limitations when As an AI-first Workflow Automation perspective. 

**n8n** is a node-based open source workflow automation platform. and enables users to link various applications. It’s strong and versatile, particularly for the developers and tech teams. But, it can take technical set-up, To have knowledge of hosting, API configuration and understanding of workflow logic. Its AI agentbuilding The capabilities 

_CHAPTER 1. INTRODUCTION_ 

3 

of and native multi-model orchestration are limited as compared to the goals of FlowMind AI. 

**Make.com** offers a visual, cloud-based automation builder and has a ton of SaaS integrations. It can be used for automating business processes like email management, CRM updates, and file synchronization. But some of the more advanced functions come with APIs are typically reliant on external API configuration and used in paid plans. compared to native AI orchestration. 

**Zapier** is known as a popular solution for web app connections via trigger-action workflows. Simple automations are easy but more advanced AI workflows can be expensive. Hard to control and manage. Zapier offers some control over multi-model AI logic too. Evaluation of responses and comparisons. 

Table 1.2: Applications Comparison 

|**Features**|**N8N**<br>**Make.com**<br>**Zapier**<br>**FlowMind AI**|
|---|---|
|No-Code Workfow Builder|✓<br>✓<br>✓<br>✓|
|User Authentication|✓<br>✓<br>✓<br>✓|
|AI Agent Creation|_×_<br>_×_<br>_×_<br>✓|
|Multi-Model AI Integration|_×_<br>_×_<br>_×_<br>✓|
|Comparative AI Response|_×_<br>_×_<br>_×_<br>✓|
|Real-Time Monitoring|_×_<br>_×_<br>_×_<br>✓|
|API & Webhook Integra-<br>tion|✓<br>✓<br>✓<br>✓|
|Drag-and-Drop Interface|✓<br>✓<br>✓<br>✓|
|Afordable Core Access|_×_<br>_×_<br>_×_<br>✓|
|Role-Based Access Control|✓<br>✓<br>✓<br>✓|
|Analytics Dashboard|_×_<br>_×_<br>_×_<br>✓|
|Scalability Support|✓<br>✓<br>✓<br>✓|



## **1.2.2 Future System Usage Analysis** 

FlowMind AI is expected to be used by freelancers, students, startups, content creators, small businesses, and enterprises that need easy access to AI automation. Users will be able to build workflows for content generation, summarization, customer support, data formatting, decision assistance, API orchestration, and repetitive task automation. 

_CHAPTER 1. INTRODUCTION_ 

4 

In future versions, the system can be expanded to include advanced conditional workflow logic, loops, branching, collaborative workflow editing, advanced analytics, marketplace-based workflow sharing, enhanced billing, and cloud deployment. The platform may also support additional AI providers, more third-party integrations, and prebuilt workflow templates for different industries. 

## **1.3 Objectives** 

The main objective of FlowMind AI is to develop an intelligent web-based no-code workflow automation platform that enables users to create, execute, and monitor AIdriven workflows without programming knowledge. 

The specific objectives of the project are as follows: 

- To design and develop a web-based platform using Next.js and React. 

- To implement secure user authentication using Firebase Authentication. 

- To use Firebase Firestore for storing user profiles, workflows, execution logs, templates, analytics, and notifications. 

- To develop a drag-and-drop workflow builder using a node-based canvas. 

- To allow users to create, configure, save, update, delete, and reuse workflows. 

- To integrate multiple AI providers including OpenAI, Gemini, Claude, and other compatible APIs. 

- To provide workflow execution support for AI nodes and integration nodes. 

- To provide analytics and monitoring features for workflow performance. 

- To develop separate user and admin panels with role-based access. 

- To support templates, notifications, marketplace-related features, billing, integrations, and audit logs as extended platform capabilities. 

## **1.4 Problem Statement / Limitations** 

AI has grown at an accelerated pace, and developing tailored AI models has been a challenge. AI workflows are still not easy for non-technical users. Many users want to automate! The use of AI for tasks is challenging, with issues like programming requirements, complex API configuration, model integration, data management, and third-party integration. These challenges limit the practical use of AI automation for students, freelancers, small businesses, and startups. 

There are various partial solutions already available in the form of existing workflow automation solutions, which fail to fully solve The needs of AI-first workflow orchestration. Some platforms are developeroriented, while others are expensive for advanced usage. Many platforms don’t offer End-to-end multi-model AI orchestration, comparative AI responses, AI-specific workflow nodes, real-time analytics and cheap access to advanced features. Another significant restriction is that there is no transparency during the workflow run time. 

Users frequently want to find out if a workflow completed successfully, how long the workflow took, What was output and if there was an error. Without monitoring and Without analytics, users are not easily able to improve their workflows. Hence, a web 

_CHAPTER 1. INTRODUCTION_ 

5 

based platform that makes it easier to create AI workflows is needed. Accesses various AI models, user management and more via a visual no-code interface. safely, stores workflow data reliably, provides analytics and offers separate Normal users and administrators access. FlowMind AI aims to solve the challenge of 

## **1.5 Proposed Solution** 

The solution that has been proposed is FlowMind AI, a no-code AI workflow automation available through the web. platform The system offers a visual design environment for creating workflows and adding and connecting nodes on a canvas. Each node represents a particular function such as AI or user input. processing, API integration, data transformation, template usage, notification creation or output display. FlowMind AI uses Firebase Authentication for secure login and Firebase Firestore for data storage. The Frontend is created with Next.js and React and the Backend is created with Python FastAPI. The backend provides REST APIs for workflow control, authentication validation, analytics, template, marketplace, notification, billing, audit logs and administration. 

## **1.5.1 User Module:** 

- Firebase Authentication: Register and Login.. 

- Administer user profile and account information. 

- Log in to user dashboard and saved workflows. 

- Run work flows and view the results.. 

- View workflow analytics and notifications. 

## **1.5.2 Workflow Builder Module:** 

- Create workflows using a drag-and-drop canvas. 

- Add, move and connect workflow nodes, configure and delete them. 

- Save and edit workflow structures. 

- Specify data and control flow with node connections. 

## **1.5.3 AI Integration Module:** 

- Connect workflows to OpenAI, Gemini, Claude, and other AI providers. 

- Set up prompts, model selection, and response parameters. 

- Generate AI responses within workflows. 

- Enable evaluation of AI responses in the future. 

## **1.5.4 Workflow Execution Module:** 

- Perform workflows based on the connected node structure. 

- Process input, AI, API, and output nodes. 

- Store execution results, status and error logs. 

- Deliver the finished product to the user interface. 

_CHAPTER 1. INTRODUCTION_ 

6 

## **1.5.5 Analytics and Monitoring Module:** 

- Monitor the number of executions, response time, success rate, error rate and token usage. 

- Visualize the workflow performance with charts and dashboards 

- Enable admin level platform activity monitoring 

## **1.5.6 Admin Panel Module:** 

- Manage Users, Workflows, Templates, Notifications & System Activity 

- Check analytics and audit logs. 

- Track information about billing, marketplace. 

- Normal user & administrator functions separated. 

## **1.5.7 Integration and Template Module:** 

- External API and Webhook Integration Support. 

- Reusable workflow templates are permitted. 

- Bookmarking, rating, cloning and searching templates 

## **1.6 Intended Market of Product** 

FlowMind AI’s target audience is students, freelancers, startups, small and mediumsized businesses, content creators, developers and enterprises that need intelligent workflow automation. The platform will be especially useful for those who want to use AI to drive productivity and automation, but who don’t want to code or deal with the management of AI systems. 

Manually handle complex API integrations.Because there is a market demand for AI productivity tools and no-code platforms is increasing. Numerous organizations are interested in implementing AI but lack AI engineering teams dedicated to the task. 

FlowMind AI delivers an easy-to-use, affordable and accessible AI workflow solution to eliminate repetitive tasks, enhance decision making,and contributing to digital transformation. Marketing agencies, customer support teams, software companies, and others are among the potential market segments. teams, academic users, research teams, business analysts and small businesses. The platform may also have future commercial features, like subscription plans, Marketplace templates, paid automation resources, and enterprise integrations. 

## **1.7 Intended Users of Product** 

FlowMind AI is designed for both normal users and administrators. Normal users include students, freelancers, content creators, business owners, developers, scientists and start-up groups. These users can establish workflows, set up AI configurations, and more. Prompt, run workflows, access templates, view outputs, and view analytics. They The no-code interface is beneficial to those who don’t have a lot of programming experience. Platform management is the responsibility of the administrators. They can 

_CHAPTER 1. INTRODUCTION_ 

7 

keep track of the users,workflows, analytics, notifications, templates, marketplace items, billing information, and audit logs. 

The backend management panel of this platform is capable of system management and control, activity auditing, and platform governance support. It also integrates with external entities including AI service providers and Firebase to provide five core supporting services, including identity verification. 

## **1.8 Software Process Model** 

The FlowMind AI development process is inspired by the Agile Scrum process model. Agile is Modular system with modules such as user authentication, administration etc. are available which makes it suitable for this project. Workflow builder, AI integration, analytics, admin panel, templates, integrations. and billing. These modules can be developed, tested and improved by an iterative process. sprints. 

## **1.8.1 Process Model Introduction** 

In Agile Scrum, software development work is broken down into Small development cycles (sprints). Each sprint concentrates on a set of features or improvements. The team checks progress and tests what has been developed at the end of each sprint. modules and adjusts the plan as per feedback and project requirements. 

Figure 1.1: Agile Scrum Framework 

## **1.8.2 Justification of Proposing the process model** 

The Agile Scrum model is suitable for FlowMind AI, which requires Can change over the course of development. The integration of AI, work flows, front-end usability, Designing both the front end and backend API is an ongoing process that must be continually tested and refined. Agile enables the team to work on modules concurrently and get feedback and improve without waiting. 

The project will be monitored from start to finish. The three project members can also collaborate through Agile. Frontend development, backend development, UI/UX design, testing and documentation can be handed over. in sprints. This will reduce the chance of development failure, and enable at least part of the functionality to be available In the initial phase of the project. 

## **1.8.3 Steps of Process Model** 

In Agile Scrum there are the following processes: 

- **Requirement Analysis:** Scope, Users, Modules, Functional Requirements, 

- **Sprint Planning:** Chop up the project into smaller chunks and assign work 

_CHAPTER 1. INTRODUCTION_ 

8 

- **Design:** Develop graphics of architecture, database model, UI design and system diagrams. 

- **Implementation:** Frontend Parts, Backend APIs, Firebase Integration, AI services, workflow builder, and more. 

- **Testing:** Test modules one-by-one and test integrated workflows. 

- **Review and Feedback:** With the completed features, review and improve the system based on the features on feedback. 

- **Documentation:** Keep project documentation, diagrams and reports up to date throughout development. 

## **Chapter 2 SOFTWARE REQUIREMENTS SPECIFICATION** 

The Software Requirements Specification is a document that specifies the functional and non-functional requirements. of FlowMind AI. It states the purpose of the system, how the users, who will use the platform and what are the constraints to take into account in the design. and implementation. By having a defined SRS, this helps the team build the system according to defined sets goals and offers a reference for testing and evaluation. 

## **2.1 Introduction** 

The FlowMind AI requirements phase included a study on the existing automation platforms, identifying limitations in AI workflow creation, and defining features needed for An easy-to-use no-code AI automation solution. The system is intended to change complex Setup manual AI workflows without coding via visual platform for creating workflows, AI model integration, execution monitoring, templates, notifications, integrations, and admin management. 

## **2.1.1 Document Scope** 

This SRS document defines the scope and requirements of FlowMind AI. It covers user authentication, workflow creation, workflow management, AI integration, workflow execution, analytics, templates, notifications, integrations, billing, marketplace-related features, audit logs, and admin panel functionality. It also identifies non-functional requirements such as performance, reliability, scalability, security, usability, maintainability, compatibility, and availability. 

The document is limited to the features planned and partially implemented for the final year project. Advanced production-level features such as public deployment, enterpriselevel scaling, and full commercial marketplace operations may be completed as future work. 

## **2.1.2 Audience** 

The intended audience of this document includes project supervisors, evaluators, developers, UI/UX designers, testers, and future contributors. It is also useful for stakeholders who want to understand the system objectives, requirements, architecture, and expected behavior of FlowMind AI. 

## **2.2 Functional Requirements** 

Functional requirements are services and operations that the system must provide. provide. FlowMind AI has the following functional requirements. 

9 

_CHAPTER 2. SOFTWARE REQUIREMENTS SPECIFICATION_ 

10 

Table 2.1: Functional Requirements of FlowMind AI 

|**ID**|**Requirement Description**|
|---|---|
|FR1|The system shall allow users to register and log in using<br>Firebase Authentication.|
|FR2|The system shall verify Firebase ID tokens before allowing<br>access to protected backend APIs.|
|FR3|The system shall allow users to manage their profle<br>information.|
|FR4|The system shall provide separate access for normal users and<br>administrators.|
|FR5|The system shall allow users to create, save, update, delete,<br>and list workfows.|
|FR6|The system shall provide a visual drag-and-drop workfow<br>canvas using node-based design.|
|FR7|The system shall allow users to add, connect, confgure, and<br>remove workfow nodes.|
|FR8|The system shall support AI nodes that connect with providers<br>such as OpenAI, Gemini, and Claude.|
|FR9|The system shall execute workfows according to node and edge<br>structure.|
|FR10|The system shall store workfow data, nodes, edges, and<br>execution records in Firebase Firestore.|
|FR11|The system shall provide analytics such as execution count,<br>response time, success rate, error rate, and usage data.|
|FR12|The system shall allow users to search, clone, rate, bookmark,<br>and reuse workfow templates.|
|FR13|The system shall support notifcations and alerts related to<br>workfow and platform events.|
|FR14|The system shall provide integration and webhook support for<br>external services.|
|FR15|The system shall provide an admin panel for monitoring users,<br>workfows, analytics, audit logs, templates, billing, and<br>marketplace activity.|
|FR16|The system shall provide REST API documentation through<br>OpenAPI/Swagger.|



## **2.3 Non-Functional Requirements** 

Non-functional requirements specify a quality attribute of the system. These requirements make FlowMind AI secure, usable, maintainable and scalable. 

_CHAPTER 2. SOFTWARE REQUIREMENTS SPECIFICATION_ 

11 

## **2.3.1 Software Quality Attributes** 

- **Performance:** the system should be able to process request of users and the operations of the workflow on time to the requThe system should be able to perform the workflows consistently and save the results accurately. 

- **Scalability:** Architecture should be able to expand to accommodate more users, workflows, and AI requests. 

- **Security:** system should be secured using Firebase Authentication, Token Verification, Protected Routes, role-based access and secure environment variables. 

- **Usability:** Workflow builder and dashboard should be user friendly for those who are non-technical users. 

- **Maintainability:** Modularity of the system, Frontend, Backend, AI,Update and Firebase services can be updated separately become operational by the end of this year 

- **Availability:** The system should be available by the end of this year. provide support for future cloud deployment. 

## **2.3.2 Other Non-Functional Requirements** 

- **Platform Requirement:** The system shall be Web based and shall be available via modern browsers. The responsiveness and compatibility of the front end should be ensured. with common browsers. 

- **Compatibility Requirement:** The frontend should be responsive and compatible with common browsers. 

- **Integration Requirement:** There is a need to integrate with external AI services (APIs), Firebase, Stripe, third party APIs and services. 

- **Privacy Requirement:** Users’ data and API keys must be safeguarded and not part of public repository or documentation. 

- **Deployment Requirement:** The current system is deployed locally, public deployment is desired. Future work is planned to deploy this on public repository. 

## **2.4 Requirement Gathering Techniques Used** 

To gather the requirements multiple techniques were used to ensure that FlowMind AI meets actual user requirements and caters to the current market constraints. 

## **2.4.1 Focus Group** 

Informal meetings held with team, students and possible Identify common problems for users when using AI tools and workflow automation platforms. These conversations led to the realisation of the need for a visual no-code workflow builder and Easy AI model settings. 

## **2.4.2 User Observation** 

The team witnessed the actual usage of the current AI tools and automation platforms. Many users were found to be using manual copying and prompt rewriting and repeated copying. API calls, as well as separate tools for automation. These observations were 

_CHAPTER 2. SOFTWARE REQUIREMENTS SPECIFICATION_ 

12 

used to help identify the need. for workflow nodes and workflow templates that are connected. 

## **2.4.3 Analyze Existing Systems** 

The current systems like n8n, Make.com and Zapier were analysed to understand the features and restrictions of their use. This analysis helped to identify gaps in multi-model AI orchestration, cost, AI-specific workflow design, analysis, and usability (non-technical). 

## **2.5 Time Frame** 

Requirement gathering and analysis was done at an early stage. The Final Year project is a part of the requirements for the BSc. Degree. The phase involved the literature review, existing system analysis, specification.Analysis of user needs and identification of modules and preparation of functional and nonfunctional specification. requirements.. 

Table 2.2: Project Time Frame 

|**Activity**|**Description**|**Duration**|
|---|---|---|
|Requirement Analysis|Identify users, modules, and<br>system requirements|2 Weeks|
|System Design|Prepare architecture, diagrams,<br>and database model|3 Weeks|
|Frontend Development|Develop dashboard, workfow<br>builder, and UI modules|5 Weeks|
|Backend Development|Develop FastAPI services and<br>Firebase integration|5 Weeks|
|AI Integration|Connect AI providers and<br>workfow AI nodes|4 Weeks|
|Testing and Debugging|Verify functional and<br>non-functional requirements|4 Weeks|
|Documentation|Prepare report, diagrams, and<br>presentation material|Continuous|



## **Chapter 3** 

## **SOFTWARE PROJECT PLAN** 

The Software Project Plan outlines the development, management, scheduling, monitored, and delivered. It determines what the project is going to produce, what the project management is going to involve, scheduling approach, assumptions, constraints and risk management strategies. The The intent of this chapter is to insure that the project is accomplished in an organized manner. 

## **3.1 Deliverables of the Project** 

The FlowMind AI project will produce both software and documentation deliverables. The main deliverable is a working web-based AI workflow automation platform that allows users to create, configure, execute, and monitor AI-driven workflows through a visual nocode interface. 

The project deliverables include: 

- Next.js and React based frontend application. 

- Python FastAPI backend with REST API endpoints. 

- Firebase Authentication integration for user login and registration. 

- Firebase Firestore data storage for users, workflows, executions, templates, notifications, analytics, and admin data. 

- Visual workflow builder using node-based drag-and-drop interaction. 

- AI integration with OpenAI, Gemini, Claude, and compatible providers. 

- User dashboard and admin panel. 

- Analytics and monitoring interface. 

- API documentation through OpenAPI/Swagger. 

- UML diagrams, DFDs, ERD/Firestore data model, and system design diagrams. 

- Final report and presentation material. 

## **3.2 Software Project Management Plan** 

The Software Project Management Plan is concerned with planning, organizing, monitoring, and controlling project activities. It ensures that the project is completed within the academic timeframe and according to defined requirements. 

## **3.2.1 Project Planning** 

Project planning includes identification of tasks, allocation of responsibilities, estimation of resources, quality planning, and scheduling of development activities. 

**3.2.1.1 Milestones Plan** The major milestones of FlowMind AI include requirement analysis, system design, frontend development, backend development, Firebase integration, workflow builder development, AI integration, analytics/admin module development, testing, and documentation. 

13 

_CHAPTER 3. SOFTWARE PROJECT PLAN_ 

14 

**3.2.1.2 Documentation Plan** The documentation plan includes preparation of project overview, SRS, software project plan, functional analysis and modeling, system design, interface design, test plan, user manual, conclusion, and references. As of the current phase, documentation is prepared up to Chapter 5. 

**3.2.1.3 Resources Plan** The resources required for the project include development laptops, Visual Studio Code, Firebase project, AI provider API keys, Node.js, Python, FastAPI, browser testing tools, Git/GitHub, and Overleaf for documentation. 

**3.2.1.4 Quality Plan** Quality is maintained through modular development, code review, functional testing, integration testing, UI review, requirement validation, and supervisor feedback. The team ensures that each module is tested before integration with the complete system. 

## **3.2.2 Project Scheduling** 

Project scheduling defines the sequence and duration of development activities. It helps the team track progress and complete the project within the academic deadline. 

Figure 3.1: Gantt Chart 

## **3.2.2.1 Gantt Chart** 

_CHAPTER 3. SOFTWARE PROJECT PLAN_ 

15 

Figure 3.2: Work Break Down Structure 

## **3.2.2.2 Work Breakdown Structure** 

Figure 3.3: Critical Path 

## **3.2.2.3 Critical Path Method** 

## **3.3 Managerial Process** 

## **3.3.1 Management Objectives and Priorities** 

Main Management Goal: Complete FlowMind AI in the last year To deliver the project within the project time frame according to the functional and non-functional requirements. The project priorities are reliable authentication, usable workflow builder, correct authentication of the parties, and correct backend API behavior, AI integration, secure data storage, separation of admin/user access, and complete documentation. Collaboration, task distribution, progress tracking and quality are other important factors that the team takes into account. assurance. Each member is responsible for contributing according to his/her assigned responsibilities and also To support integration and testing activities. 

The team also prioritizes collaboration, task distribution, progress tracking, and quality assurance. Each member contributes according to assigned responsibilities while also supporting integration and testing activities. 

## **3.3.2 Assumptions and Constraints** 

The project is based on the following assumptions: 

- Users will have an Internet connection and an up-to-date web browser. 

- All Firebase services will continue to operate during development and testing. 

- API keys are going to be provided by AI providers and will be configured to allow access to AI provider APIs. 

- The chosen technologies are adequate to achieve the necessary modules. 

The project has the following constraints: 

- **Time Constraint:** Project should be completed within the academic time frame. 

- **Resource Constraint:** Three students are developing the project. 

_CHAPTER 3. SOFTWARE PROJECT PLAN_ 

16 

- **Technical Constraint:** AI APIs might have rate limiting or latency or cost restrictions. 

- **Deployment Constraint:** The current version runs locally and public deployment is planned as future work. 

- **Security Constraint:** API keys and Firebase credentials should be safeguarded and not exposed. 

## **3.4 Project Risk Management** 

Risk management is a process in which the potential problems that could impact project schedule, quality, performance, or completion. FlowMind AI relies on the frontend, backend, Firebase For successful AI API integration, services and external integrations, risk management is important. development. 

## **3.4.1 Risk Management Plan** 

The risk management plan includes risk identification, risk analysis, mitigation planning, monitoring, and control. Risk are analysed during development and appropriate Steps are taken to minimise their effects. 

**3.4.1.1 Purpose** To identify possible risks take early and prepare mitigation strategies. This ensures that the team do not experience delays and technical 

- **3.4.1.2 Roles and Responsibilities** 

   - **Project Team:** Project risks are identified and reported during the development of the project. 

   - **Frontend Developer:** UI, canvas of the workflow, responsiveness, usability management risks. 

   - **Backend Developer:** The Backend Developer will be responsible for handling API, Firebase, AI integration, and performance. risks. 

   - **UI/UX Designer:** Handle risks of clarity of interfaces and usability. 

   - **Supervisor:** Give direction and check the development of the project. 

## **3.4.2 Risk Management Activities** 

Table 3.1: Risk Identification Table 

|**ID**|**Risk**|**Likelihood**|**Impact**|
|---|---|---|---|
|R1|AI provider API failure, latency, or rate<br>limits|Medium|High|
|R2|Firebase authentication or Firestore<br>confguration issues|Medium|High|
|R3|Workfow execution logic becomes<br>complex|High|High|
|R4|User interface becomes difcult for<br>non-technical users|Medium|Medium|
|R5|Local development environment issues|Medium|Medium|
|R6|Security exposure of API keys or<br>credentials|Low|High|
|R7|Delay in documentation and diagram<br>preparation|Medium|Medium|



## **3.4.2.1 Risk Identification** 

_CHAPTER 3. SOFTWARE PROJECT PLAN_ 

17 

**3.4.2.2 Risk Analysis** Risk Analysis Risks having a high impact and medium or high likelihood are prioritized. AI API dependency, Firebase configuration, workflow execution logic and the security of credentials are deemed to be the most critical risks as they directly impact The impact of the systems on functionality and reliability. 

**3.4.2.3 Rating Risk Likelihood and Impact** Risks are rated as Low, Medium, or High based on their probability and effect on the project. High-impact risks are monitored continuously. 

Table 3.2: Risk and Mitigation Strategies 

|**ID**|**Risk**|**Mitigation Strategy**|
|---|---|---|
|R1|AI API failure or rate limits|Use multiple providers and<br>handle API errors gracefully.|
|R2|Firebase confguration errors|Test authentication and<br>Firestore rules early.|
|R3|Complex workfow logic|Use modular execution design<br>and test workfows incrementally.|
|R4|Difcult interface|Conduct usability review and<br>simplify workfow builder<br>actions.|
|R5|Local environment issues|Maintain setup documentation<br>and version control.|
|R6|Credential exposure|Store credentials in environment<br>variables and avoid committing<br>secrets.|
|R7|Documentation delay|Update documentation<br>continuously with development<br>progress.|



## **3.4.2.4 Risk Response Planning** 

**3.4.2.5 Risk Monitoring and Control** Risk Monitoring and Control The team monitors and revises progress regularly and identifies whether risks are becoming more or less. The risk plan, if new risks emerge, is updated. 

**3.4.2.6 Risk Assessment** Most risks can be controlled (as evidenced by the risk assessment) to achieve this by the modular development, early testing, secure configuration and continuous documentation. If the testing and integration are then the overall level of risks in the project is manageable. performed consistently. 

## **Chapter 4 FUNCTIONAL ANALYSIS AND MODELING** 

Functional analysis and modelling include how users interact with FlowMind AI and how information is passed through the system. This chapter contains use case modelling, user stories, Individual actor use cases, entity relationship design and data flow diagrams. These models aid in translating requirements to system behavior. 

## **4.1 Use Case Modeling** 

Case modeling is used to discover who the actors are that communicate with the system, and what the functions are. they perform. FlowMind AI has Normal User, Administrator and Firebase as its main actors. Authentication, AI Providers, Stripe and Third-party APIs. 

Figure 4.1: Use case Diagram 

18 

_CHAPTER 4. FUNCTIONAL ANALYSIS AND MODELING_ 

19 

## **4.1.1 User Stories** 

Table 4.1: User Stories of FlowMind AI 

|**ID**|**Actor**|**User Story**|
|---|---|---|
|US1|Normal User|As a user, I want to register and log in<br>securely so that I can access my<br>workfows.|
|US2|Normal User|As a user, I want to create workfows<br>visually so that I can automate tasks<br>without coding.|
|US3|Normal User|As a user, I want to confgure AI nodes<br>so that I can generate outputs using<br>selected AI models.|
|US4|Normal User|As a user, I want to execute workfows so<br>that I can automate repetitive processes.|
|US5|Normal User|As a user, I want to view analytics so<br>that I can understand workfow<br>performance.|
|US6|Normal User|As a user, I want to use templates so<br>that I can create workfows quickly.|
|US7|Administrator|As an administrator, I want to manage<br>users so that I can control platform<br>access.|
|US8|Administrator|As an administrator, I want to monitor<br>workfows and analytics so that I can<br>evaluate system activity.|
|US9|Administrator|As an administrator, I want to review<br>audit logs so that I can track important<br>system events.|
|US10|External AI Provider|As an AI provider, I receive prompts and<br>return generated responses to the<br>workfow engine.|



_CHAPTER 4. FUNCTIONAL ANALYSIS AND MODELING_ 

20 

## **4.1.2 Individual Actor Use Cases** 

Table 4.2: Use Case Table of Register User 

|**Use Case Name**|Register User|
|---|---|
|**Actor**|Normal User|
|**Description**|The user creates an account using email and<br>password through Firebase Authentication.|
|**Precondition**|User is not already logged in.|
|**Postcondition**|User account and profle are created successfully.|
|**Main Flow**|User enters details, Firebase creates account,<br>backend stores profle, and dashboard is shown.|



Table 4.3: Use Case Table of Authenticate User 

|**Use Case Name**|Authenticate User|
|---|---|
|**Actor**|Normal User, Administrator|
|**Description**|The user logs into the system and receives<br>authenticated access.|
|**Precondition**|User account exists.|
|**Postcondition**|User is redirected to dashboard or admin panel<br>according to role.|
|**Main Flow**|User submits credentials, Firebase verifes them,<br>backend verifes token, and role-based screen is<br>displayed.|



Table 4.4: Use Case Table of Create Workflow 

|**Use Case Name**|Create Workfow|
|---|---|
|**Actor**|Normal User|
|**Description**|The user creates a new workfow using the visual<br>workfow builder.|
|**Precondition**|User is authenticated.|
|**Postcondition**|Workfow is saved in Firestore.|
|**Main Flow**|User opens builder, creates workfow, adds nodes,<br>connects edges, confgures settings, and saves<br>workfow.|



_CHAPTER 4. FUNCTIONAL ANALYSIS AND MODELING_ 

21 

Table 4.5: Use Case Table of Configure AI Nodes 

|**Use Case Name**|Confgure AI Nodes|
|---|---|
|**Actor**|Normal User|
|**Description**|The user confgures AI node prompt, model, and<br>parameters.|
|**Precondition**|Workfow canvas is open and AI node is added.|
|**Postcondition**|AI node confguration is saved.|
|**Main Flow**|User selects AI node, chooses provider/model,<br>enters prompt, adjusts parameters, and saves<br>settings.|



Table 4.6: Use Case Table of Execute Workflow 

|**Use Case Name**|Execute Workfow|
|---|---|
|**Actor**|Normal User|
|**Description**|The user runs a saved workfow and receives<br>output.|
|**Precondition**|Workfow is valid and saved.|
|**Postcondition**|Execution result and logs are stored.|
|**Main Flow**|User clicks execute, backend retrieves workfow,<br>execution service processes nodes, AI provider<br>returns response, and fnal output is displayed.|



Table 4.7: Use Case Table of View Analytics 

|**Use Case Name**|View Analytics|
|---|---|
|**Actor**|Normal User, Administrator|
|**Description**|The user views workfow metrics and system<br>performance data.|
|**Precondition**|Execution data exists.|
|**Postcondition**|Analytics dashboard is displayed.|
|**Main Flow**|User opens analytics, backend retrieves metrics,<br>and charts are displayed in the dashboard.|



_CHAPTER 4. FUNCTIONAL ANALYSIS AND MODELING_ 

22 

Table 4.8: Use Case Table of Manage Templates 

|**Use Case Name**|Manage Templates|
|---|---|
|**Actor**|Normal User, Administrator|
|**Description**|Users can create, search, clone, rate, and<br>bookmark templates.|
|**Precondition**|User is authenticated.|
|**Postcondition**|Template operation is completed.|
|**Main Flow**|User opens templates, selects template, clones or<br>rates it, and system updates Firestore.|



Table 4.9: Use Case Table of Manage Integrations 

|**Use Case Name**|Manage Integrations|
|---|---|
|**Actor**|Normal User, Administrator|
|**Description**|Users connect external APIs or webhook services<br>with workfows.|
|**Precondition**|User is authenticated and integration is available.|
|**Postcondition**|Integration connection is stored or updated.|
|**Main Flow**|User selects integration, provides confguration,<br>tests connection, and saves it.|



Table 4.10: Use Case Table of Admin Dashboard 

|**Use Case Name**|Admin Dashboard|
|---|---|
|**Actor**|Administrator|
|**Description**|Administrator monitors users, workfows,<br>analytics, audit logs, billing, and marketplace<br>activity.|
|**Precondition**|Administrator is authenticated.|
|**Postcondition**|Admin can view and manage platform<br>information.|
|**Main Flow**|Admin opens panel, selects module, performs<br>management action, and system records audit log.|



## **4.2 Functional Modeling** 

Information Flow: Functional modeling represents the way data is structured and how information flows. between user, process, data store and external services. 

## **4.2.1 Entity Relationship Diagram** 

Although Firebase Firestore is a NoSQL document database, an ERD-style data model is used to represent the logical relationship between major collections. The main collections include users, workflows, executions, analytics, notifications, templates, integrations, marketplace, billing, and audit logs. 

_CHAPTER 4. FUNCTIONAL ANALYSIS AND MODELING_ 

23 

Figure 4.2: ERD Diagram 

## **4.2.2 Data Flow Diagram** 

Data Flow Diagrams represent how information flows through FlowMind AI. The diagrams show interaction between users, administrators, Firebase services, the FastAPI backend, Firestore, AI providers, Stripe, and third-party APIs. 

_CHAPTER 4. FUNCTIONAL ANALYSIS AND MODELING_ 

24 

Figure 4.3: DFD Level 0 Diagram 

**4.2.2.1 DFD Level 0** DFD Level 0 presents FlowMind AI as a single system. Normal users and administrators interact with the platform, while Firebase, AI providers, and external services support authentication, storage, AI generation, billing, and integrations. 

Figure 4.4: DFD Level 1 Diagram 

**4.2.2.2 DFD Level 1** DFD Level 1 expands the system into major processes such as authentication management, workflow management, workflow execution, AI integration, analytics, templates, marketplace, integrations, billing, admin management, notifications, and audit logs. 

Figure 4.5: DFD Level 2 Diagram 

_CHAPTER 4. FUNCTIONAL ANALYSIS AND MODELING_ 

25 

**4.2.2.3 DFD Level 2** DFD Level 2 explains the workflow execution process in more detail. The system validates the workflow, loads nodes and edges, determines execution order, processes nodes, calls AI or external APIs if required, stores execution results, updates analytics, and returns output to the user. 

## **Chapter 5 SYSTEM DESIGN** 

This chapter presents the system design of FlowMind AI. It includes structural diagrams and behavioral diagrams that explain the static structure and dynamic behavior of the system. The design is based on the requirements, functional analysis, and modeling presented in previous chapters. 

## **5.1 Structure Diagrams** 

Structure diagrams describe the static structure of the system, including classes, components, deployment nodes, and relationships between system parts. 

## **5.1.1 Class Diagram** 

The class diagram is the main logical classes and data entities of FlowMind AI. These are such as User, Admin, Workflow, WorkflowNode, Execution, AIService, Integration, Notification, Billing, Template and Analytics. The diagram illustrates the manner in which users workflows are created, nodes are added to the workflows, executions utilize AI services, and analytics are created based on execution data. 

Figure 5.1: Class Diagram 

## **5.1.2 Deployment Diagrams** 

The deployment diagram illustrates the local deployment of the FlowMind AI. external cloud services and the environment. The current version is run locally, with Next.js frontend running locally, and FastAPI backend running via Uvicorn. Firebase Authentication and Firestore are services that are accessed via the cloud. AI providers, Stripe, and third-party APIs are external services that are used by the backend. 

26 

_CHAPTER 5. SYSTEM DESIGN_ 

27 

Figure 5.2: Deployment 

## **5.2 Behavioral Diagrams** 

Behavioral diagrams describe how the system behaves during user interactions and workflow execution. These diagrams include activity diagrams, communication diagrams, and sequence diagrams. 

## **5.2.1 Activity Diagrams** 

The activity diagram shows the steps followed by a user to create and execute a workflow. The process begins with login, continues with workflow creation, node configuration, saving, validation, execution, AI provider communication, logging, analytics update, and output display. 

_CHAPTER 5. SYSTEM DESIGN_ 

28 

Figure 5.3: Activity Diagram 

## **5.2.2 Communication Diagrams** 

The communication diagram shows object-level interaction during workflow execution. It explains how the user, frontend, Firebase Authentication, FastAPI backend, Firestore, execution service, AI provider, and analytics service communicate with one another. 

_CHAPTER 5. SYSTEM DESIGN_ 

29 

Figure 5.4: Communication Diagram 

## **5.2.3 Sequence Diagrams** 

Sequence diagrams explain the order of messages exchanged between system components during important use cases. 

Figure 5.5: Sequence Diagram for Register User 

**5.2.3.1 Sequence Diagram for Register User** In this process, the user enters registration details through the frontend. Firebase Authentication creates the account and returns an ID token. The frontend sends the user profile and token to the FastAPI backend. The backend verifies the token and stores user profile information in Firestore. 

_CHAPTER 5. SYSTEM DESIGN_ 

30 

Figure 5.6: Sequence Diagram for Authenticate User 

**5.2.3.2 Sequence Diagram for Authenticate User** In this process, the user enters login credentials. Firebase Authentication verifies the credentials and returns an ID token. The frontend sends protected requests to the FastAPI backend with the token. The backend verifies the token and fetches the user profile and role from Firestore. 

_CHAPTER 5. SYSTEM DESIGN_ 

31 

Figure 5.7: Sequence Diagram for Create Workflow 

**5.2.3.3 Sequence Diagram for Create Workflow** This sequence shows how a user creates and saves a workflow. The frontend collects workflow details, nodes, and edges, then sends them to the backend. The backend stores the workflow document in Firestore and returns a success response. 

_CHAPTER 5. SYSTEM DESIGN_ 

32 

Figure 5.8: Sequence Diagram for Execute Workflow 

**5.2.3.4 Sequence Diagram for Execute Workflow** During workflow execution, the backend retrieves the workflow graph from Firestore and sends it to the execution service. The execution service processes nodes in order, sends AI prompts to the selected provider, receives responses, stores execution logs, updates analytics, and returns the final result to the frontend. 

_CHAPTER 5. SYSTEM DESIGN_ 

33 

Figure 5.9: Sequence Diagram for View Analytics 

**5.2.3.5 Sequence Diagram for View Analytics** This sequence shows how analytics data is requested and displayed. The frontend requests analytics from the backend, the backend retrieves metrics from the analytics service and Firestore, and charts are displayed to the user. 

_CHAPTER 5. SYSTEM DESIGN_ 

34 

Figure 5.10: Sequence Diagram for Admin Management 

**5.2.3.6 Sequence Diagram for Admin Management** This sequence shows how an administrator accesses the admin panel, reviews users or workflows, performs an administrative action, updates Firestore, and records the activity in audit logs. 

## **5.3 System Architecture Diagram** 

The system architecture diagram provides an overall view of FlowMind AI. It shows the relationship between normal users, administrators, the Next.js frontend, Firebase Authentication, FastAPI backend, Firestore database, AI providers, Stripe services, and external APIs. 

Figure 5.11: System Architecture of FlowMind AI 

_CHAPTER 5. SYSTEM DESIGN_ 

35 

## **5.4 Component Diagram** 

The component diagram describes the major software components of FlowMind AI and the way they interact. The frontend contains authentication UI, dashboard, workflow builder, admin panel, templates/marketplace interface, and analytics UI. The backend contains authentication verification, workflow, execution, AI integration, analytics, integration, notification, billing, and admin services. 

Figure 5.12: Component Diagram of FlowMind AI 

## **5.5 Conclusion** 

This chapter introduced the system design of FlowMind AI, its structure and behavioral diagrams. The diagrams describe the organisation of the system and how the components are connected. When it comes to user deployment, user interaction with the platform and how the workflows are developed and deployed, performed, monitored and controlled. The design is aligned with the underlying goal of developing An accessible, modular and scalable no-code AI workflow automation platform. 

## **References** 

- [1] S. Russell and P. Norvig, _Artificial Intelligence: A Modern Approach_ , 4th ed. Pearson, 2021. 

- [2] W. M. P. van der Aalst, _Workflow Management: Models, Methods, and Systems_ . MIT Press, 2004. 

- [3] n8n GmbH, “n8n Workflow Automation Tool,” [Online]. Available: https://n8n.io. [Accessed: April 2026]. 

- [4] Make.com, “Make Automation Platform,” [Online]. Available: https://www.make.com. [Accessed: April 2026]. 

- [5] Zapier Inc., “Zapier Automation Platform,” [Online]. Available: https://zapier.com. [Accessed: April 2026]. 

- [6] OpenAI, “OpenAI API Documentation,” [Online]. Available: https://platform.openai.com. [Accessed: April 2026]. 

- [7] Google Firebase, “Firebase Documentation,” [Online]. Available: https://firebase.google.com/docs. [Accessed: April 2026]. 

- [8] Vercel, “Next.js Documentation,” [Online]. Available: https://nextjs.org/docs. [Accessed: April 2026]. 

- [9] FastAPI, “FastAPI Documentation,” [Online]. Available: https://fastapi.tiangolo.com. [Accessed: April 2026]. 

- [10] XYFlow, “React Flow Documentation,” [Online]. Available: https://reactflow.dev. [Accessed: April 2026]. 

- [11] Stripe, “Stripe Documentation,” [Online]. Available: https://docs.stripe.com. [Accessed: April 2026]. 

36 

