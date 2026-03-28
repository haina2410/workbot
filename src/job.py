from dataclasses import dataclass


@dataclass
class Job:
    role: str = ""
    company: str = ""
    location: str = ""
    link: str = ""
    description: str = ""
    source: str = ""
    raw_post: str = ""
