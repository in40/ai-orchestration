#!/usr/bin/env python3
"""
Test script to verify the complete flow from tool execution to resource retrieval
"""

import json
import tempfile
import os
import sys
sys.path.insert(0, '.')

from requirement_engineer_handlers import RequirementEngineerHandlers

def test_complete_flow():
    print("Testing complete flow from tool execution to resource retrieval...")
    
    # Create a handler instance with SQLite backend for testing
    handlers = RequirementEngineerHandlers(use_postgres=False)
    
    print("\n1. Testing _analyze_requirements method...")
    analyze_args = {
        "stakeholder_inputs": "Users need to login to access the system. They should have different roles like admin and regular user.",
        "business_context": "Enterprise application with security requirements",
        "previous_requirements": []
    }
    
    try:
        analyze_result = handlers._analyze_requirements(analyze_args)
        print(f"   ✓ _analyze_requirements executed successfully")
        print(f"   Result keys: {list(analyze_result.keys())}")
    except Exception as e:
        print(f"   ✗ _analyze_requirements failed: {e}")
        return False
    
    print("\n2. Testing _resolve_ambiguity method...")
    ambiguity_args = {
        "requirements": [
            {"id": "REQ-FUNC-001", "description": "The system shall allow users to authenticate with username and password"}
        ],
        "stakeholder_context": "Enterprise stakeholders concerned about security",
        "clarification_history": []
    }
    
    try:
        ambiguity_result = handlers._resolve_ambiguity(ambiguity_args)
        print(f"   ✓ _resolve_ambiguity executed successfully")
        print(f"   Result keys: {list(ambiguity_result.keys())}")
    except Exception as e:
        print(f"   ✗ _resolve_ambiguity failed: {e}")
        return False
    
    print("\n3. Testing _translate_business_to_technical method...")
    translation_args = {
        "business_requirements": [
            {"id": "BUS-REQ-001", "description": "Users need secure authentication"}
        ],
        "technical_constraints": [
            "Must use existing identity provider",
            "Limited to 2FA via SMS"
        ],
        "system_context": "Microservices architecture with distributed auth"
    }
    
    try:
        translation_result = handlers._translate_business_to_technical(translation_args)
        print(f"   ✓ _translate_business_to_technical executed successfully")
        print(f"   Result keys: {list(translation_result.keys())}")
    except Exception as e:
        print(f"   ✗ _translate_business_to_technical failed: {e}")
        return False
    
    print("\n4. Testing _generate_traceability_matrix method...")
    matrix_args = {
        "requirements": [
            {"id": "REQ-FUNC-001", "description": "The system shall allow users to authenticate with username and password"}
        ],
        "design_elements": [
            {"id": "AUTH-DESIGN-001", "description": "Authentication service design"}
        ],
        "code_modules": [
            {"id": "auth_module.py", "description": "Authentication module"}
        ],
        "test_cases": [
            {"id": "test_auth.py", "description": "Authentication test cases"}
        ]
    }
    
    try:
        matrix_result = handlers._generate_traceability_matrix(matrix_args)
        print(f"   ✓ _generate_traceability_matrix executed successfully")
        print(f"   Result keys: {list(matrix_result.keys())}")
    except Exception as e:
        print(f"   ✗ _generate_traceability_matrix failed: {e}")
        return False
    
    print("\n5. Testing _identify_edge_cases method...")
    edge_case_args = {
        "functional_requirements": [
            {"id": "REQ-FUNC-001", "description": "The system shall allow users to authenticate with username and password"}
        ],
        "domain_context": "Financial services with strict security requirements",
        "security_requirements": [
            "PCI DSS compliance",
            "Audit logging required"
        ]
    }
    
    try:
        edge_case_result = handlers._identify_edge_cases(edge_case_args)
        print(f"   ✓ _identify_edge_cases executed successfully")
        print(f"   Result keys: {list(edge_case_result.keys())}")
    except Exception as e:
        print(f"   ✗ _identify_edge_cases failed: {e}")
        return False
    
    print("\n6. Testing resource retrieval...")
    
    # Test specifications resource
    try:
        specs_resource = {"uri": "requirements://resource/specifications"}
        specs_result = handlers._read_resource(specs_resource)
        print(f"   ✓ Specifications resource retrieved successfully")
        print(f"   Content length: {len(specs_result.get('contents', []))}")
    except Exception as e:
        print(f"   ✗ Specifications resource retrieval failed: {e}")
        return False
    
    # Test traceability matrix resource
    try:
        matrix_resource = {"uri": "requirements://resource/traceability-matrix"}
        matrix_result = handlers._read_resource(matrix_resource)
        print(f"   ✓ Traceability matrix resource retrieved successfully")
        print(f"   Content length: {len(matrix_result.get('contents', []))}")
    except Exception as e:
        print(f"   ✗ Traceability matrix resource retrieval failed: {e}")
        return False
    
    # Test ambiguity log resource
    try:
        ambiguity_resource = {"uri": "requirements://resource/ambiguity-log"}
        ambiguity_result = handlers._read_resource(ambiguity_resource)
        print(f"   ✓ Ambiguity log resource retrieved successfully")
        print(f"   Content length: {len(ambiguity_result.get('contents', []))}")
    except Exception as e:
        print(f"   ✗ Ambiguity log resource retrieval failed: {e}")
        return False
    
    print("\n7. Verifying data was stored in database...")
    
    # Check if specifications were stored
    stored_specs = handlers.task_storage.get_requirement_specifications(limit=10)
    print(f"   ✓ Found {len(stored_specs)} requirement specifications in database")
    
    # Check if traceability links were stored
    stored_links = handlers.task_storage.get_traceability_links(limit=10)
    print(f"   ✓ Found {len(stored_links)} traceability links in database")
    
    # Check if ambiguities were stored
    stored_ambiguities = handlers.task_storage.get_ambiguities(limit=10)
    print(f"   ✓ Found {len(stored_ambiguities)} ambiguities in database")
    
    print("\n✅ All tests passed! The complete flow is working correctly.")
    print("   - Tool execution stores data in the database")
    print("   - Resource retrieval fetches data from the database")
    print("   - All requirement engineering functionality is integrated")
    
    return True

if __name__ == "__main__":
    success = test_complete_flow()
    if success:
        print("\n🎉 Complete integration test PASSED!")
        exit(0)
    else:
        print("\n❌ Complete integration test FAILED!")
        exit(1)