"""
Data structures for the Implementation Engineer Agent
Defines the core data models used by the agent for code generation, refactoring, and testing
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
import uuid
import time


class CodeFileType(str, Enum):
    """Enumeration of different code file types"""
    SOURCE = "source"
    TEST = "test"
    CONFIG = "config"
    DOCUMENTATION = "documentation"


class CodeQualityLevel(str, Enum):
    """Enumeration of code quality levels"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"


class CodeFile(BaseModel):
    """Represents a code file with metadata"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for the file")
    filename: str = Field(..., description="Name of the file")
    content: str = Field(..., description="Content of the file")
    language: str = Field(..., description="Programming language")
    file_type: CodeFileType = Field(..., description="Type of the code file")
    created_at: float = Field(default_factory=time.time, description="Timestamp when the file was created")
    updated_at: float = Field(default_factory=time.time, description="Timestamp when the file was last updated")
    dependencies: List[str] = Field(default=[], description="List of dependencies for this file")
    parent_module: Optional[str] = Field(None, description="Parent module or namespace")
    quality_score: Optional[float] = Field(None, description="Quality score from 0.0 to 1.0")
    quality_level: Optional[CodeQualityLevel] = Field(None, description="Quality level")


class TestSuite(BaseModel):
    """Represents a collection of unit tests"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for the test suite")
    name: str = Field(..., description="Name of the test suite")
    framework: str = Field(..., description="Testing framework used")
    tests: List[str] = Field(default=[], description="List of test code snippets")
    coverage_percentage: float = Field(0.0, description="Test coverage percentage")
    created_at: float = Field(default_factory=time.time, description="Timestamp when the suite was created")
    updated_at: float = Field(default_factory=time.time, description="Timestamp when the suite was last updated")
    target_files: List[str] = Field(default=[], description="List of files this test suite targets")
    passed_count: int = Field(0, description="Number of tests that passed")
    failed_count: int = Field(0, description="Number of tests that failed")
    skipped_count: int = Field(0, description="Number of tests that were skipped")


class RefactoringReport(BaseModel):
    """Represents a report on code refactoring"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for the report")
    original_code_id: str = Field(..., description="ID of the original code")
    refactored_code_id: str = Field(..., description="ID of the refactored code")
    refactoring_goals: List[str] = Field(default=[], description="Goals that were achieved")
    improvements_made: List[str] = Field(default=[], description="Specific improvements made")
    performance_impact: Optional[Dict[str, Any]] = Field(None, description="Performance impact metrics")
    maintainability_score_before: Optional[float] = Field(None, description="Maintainability score before refactoring")
    maintainability_score_after: Optional[float] = Field(None, description="Maintainability score after refactoring")
    created_at: float = Field(default_factory=time.time, description="Timestamp when the report was created")
    refactoring_notes: Optional[str] = Field(None, description="Additional notes about the refactoring")


class StyleGuide(BaseModel):
    """Represents a coding style guide"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for the style guide")
    name: str = Field(..., description="Name of the style guide")
    language: str = Field(..., description="Programming language the guide applies to")
    rules: List[str] = Field(default=[], description="List of style rules")
    best_practices: List[str] = Field(default=[], description="Best practices defined in the guide")
    anti_patterns: List[str] = Field(default=[], description="Anti-patterns to avoid")
    created_at: float = Field(default_factory=time.time, description="Timestamp when the guide was created")
    updated_at: float = Field(default_factory=time.time, description="Timestamp when the guide was last updated")
    version: str = Field("1.0.0", description="Version of the style guide")


class ImplementationTask(BaseModel):
    """Represents a task for the Implementation Engineer Agent"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for the task")
    title: str = Field(..., description="Title of the task")
    description: str = Field(..., description="Detailed description of the task")
    task_type: str = Field(..., description="Type of task (code_generation, refactoring, testing, etc.)")
    priority: int = Field(5, description="Priority of the task (1-10)")
    status: str = Field("pending", description="Current status of the task")
    created_at: float = Field(default_factory=time.time, description="Timestamp when the task was created")
    updated_at: float = Field(default_factory=time.time, description="Timestamp when the task was last updated")
    assigned_to: Optional[str] = Field(None, description="Agent or person assigned to the task")
    estimated_duration: Optional[int] = Field(None, description="Estimated duration in minutes")
    actual_duration: Optional[int] = Field(None, description="Actual duration in minutes")
    dependencies: List[str] = Field(default=[], description="IDs of dependent tasks")
    artifacts: List[str] = Field(default=[], description="Generated artifacts from the task")
    requirements: List[str] = Field(default=[], description="Requirements for the task")
    architectural_guidelines: List[str] = Field(default=[], description="Architectural guidelines to follow")


class CodeReview(BaseModel):
    """Represents a code review"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for the review")
    code_file_id: str = Field(..., description="ID of the code file being reviewed")
    reviewer: str = Field(..., description="Reviewer's name or ID")
    review_date: float = Field(default_factory=time.time, description="Date of the review")
    comments: List[str] = Field(default=[], description="Review comments")
    suggestions: List[str] = Field(default=[], description="Suggestions for improvement")
    approval_status: str = Field("pending", description="Approval status (approved, rejected, needs_work)")
    quality_score: Optional[float] = Field(None, description="Quality score from 0.0 to 1.0")
    issues_found: List[str] = Field(default=[], description="Issues identified during review")
    severity_distribution: Dict[str, int] = Field(default={}, description="Distribution of issue severities")


class ProjectContext(BaseModel):
    """Represents the context of a software project"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for the project")
    name: str = Field(..., description="Name of the project")
    description: str = Field("", description="Description of the project")
    programming_language: str = Field(..., description="Main programming language")
    framework: str = Field("", description="Framework used in the project")
    architecture: str = Field("", description="Architectural pattern used")
    created_at: float = Field(default_factory=time.time, description="Timestamp when the project was created")
    updated_at: float = Field(default_factory=time.time, description="Timestamp when the project was last updated")
    code_files: List[CodeFile] = Field(default=[], description="List of code files in the project")
    test_suites: List[TestSuite] = Field(default=[], description="List of test suites for the project")
    style_guides: List[StyleGuide] = Field(default=[], description="List of style guides for the project")
    dependencies: List[str] = Field(default=[], description="Project dependencies")
    version_control_url: Optional[str] = Field(None, description="URL of the version control repository")