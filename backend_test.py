#!/usr/bin/env python3

import requests
import json
import sys
from datetime import datetime, timezone

class ConsultingWorkflowTester:
    def __init__(self):
        self.base_url = "https://erp-unified-flow.preview.emergentagent.com/api"
        self.token = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.created_resources = {
            'users': [],
            'leads': [],
            'projects': [],
            'meetings': []
        }
        
    def log_test(self, name, success, details=""):
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED")
        else:
            print(f"❌ {name} - FAILED: {details}")
        
    def make_request(self, method, endpoint, data=None, expected_status=200):
        """Make HTTP request with error handling"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
            
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10)
            else:
                return False, {"error": "Invalid method"}
                
            success = response.status_code == expected_status
            try:
                response_data = response.json()
            except:
                response_data = {"message": response.text, "status_code": response.status_code}
                
            return success, response_data
            
        except requests.exceptions.RequestException as e:
            return False, {"error": str(e)}
    
    def test_user_registration_and_login(self):
        """Test user registration and login for all roles"""
        print("\n🔐 Testing Authentication...")
        
        # Test registration for different roles
        roles = ['admin', 'manager', 'executive']
        test_timestamp = datetime.now().strftime("%H%M%S")
        
        for role in roles:
            # Register user
            user_data = {
                "email": f"test_{role}_{test_timestamp}@example.com",
                "password": "TestPass123!",
                "full_name": f"Test {role.title()}",
                "role": role,
                "department": "Testing"
            }
            
            success, response = self.make_request('POST', 'auth/register', user_data, 200)
            self.log_test(f"Register {role} user", success, response.get('detail') if not success else "")
            
            if success:
                self.created_resources['users'].append(response)
                
                # Test login
                login_data = {
                    "email": user_data["email"],
                    "password": user_data["password"]
                }
                
                success, login_response = self.make_request('POST', 'auth/login', login_data, 200)
                self.log_test(f"Login {role} user", success, login_response.get('detail') if not success else "")
                
                if success and role == 'admin':  # Use admin for further tests
                    self.token = login_response.get('access_token')
                    self.user_id = login_response.get('user', {}).get('id')
                    
                    # Test /auth/me endpoint
                    success, me_response = self.make_request('GET', 'auth/me', None, 200)
                    self.log_test("Get current user info", success, me_response.get('detail') if not success else "")
    
    def test_leads_management(self):
        """Test leads CRUD operations"""
        print("\n👥 Testing Leads Management...")
        
        if not self.token:
            print("❌ No authentication token available for leads tests")
            return
            
        # Create lead
        lead_data = {
            "first_name": "John",
            "last_name": "Doe",
            "company": "Test Company",
            "job_title": "CEO",
            "email": "john.doe@testcompany.com",
            "phone": "+1234567890",
            "linkedin_url": "https://linkedin.com/in/johndoe",
            "source": "Website",
            "notes": "High priority lead from demo request",
            "status": "new"
        }
        
        success, response = self.make_request('POST', 'leads', lead_data, 200)
        self.log_test("Create lead", success, response.get('detail') if not success else "")
        
        if success:
            lead_id = response.get('id')
            self.created_resources['leads'].append(response)
            
            # Test get single lead
            success, get_response = self.make_request('GET', f'leads/{lead_id}', None, 200)
            self.log_test("Get single lead", success, get_response.get('detail') if not success else "")
            
            # Test update lead
            update_data = {
                "status": "contacted",
                "notes": "Updated notes after first contact"
            }
            success, update_response = self.make_request('PUT', f'leads/{lead_id}', update_data, 200)
            self.log_test("Update lead", success, update_response.get('detail') if not success else "")
        
        # Test get all leads
        success, all_leads = self.make_request('GET', 'leads', None, 200)
        self.log_test("Get all leads", success, all_leads.get('detail') if not success else "")
        
        # Test lead filtering by status
        success, filtered_leads = self.make_request('GET', 'leads?status=new', None, 200)
        self.log_test("Filter leads by status", success, filtered_leads.get('detail') if not success else "")
    
    def test_projects_management(self):
        """Test projects CRUD operations"""
        print("\n📊 Testing Projects Management...")
        
        if not self.token:
            print("❌ No authentication token available for projects tests")
            return
            
        # Create project
        project_data = {
            "name": "Digital Transformation Initiative",
            "client_name": "Test Client Corp",
            "start_date": datetime.now(timezone.utc).isoformat(),
            "end_date": None,
            "total_meetings_committed": 10,
            "budget": 50000.0,
            "notes": "Major consulting project for digital transformation"
        }
        
        success, response = self.make_request('POST', 'projects', project_data, 200)
        self.log_test("Create project", success, response.get('detail') if not success else "")
        
        if success:
            project_id = response.get('id')
            self.created_resources['projects'].append(response)
            
            # Test get single project
            success, get_response = self.make_request('GET', f'projects/{project_id}', None, 200)
            self.log_test("Get single project", success, get_response.get('detail') if not success else "")
        
        # Test get all projects
        success, all_projects = self.make_request('GET', 'projects', None, 200)
        self.log_test("Get all projects", success, all_projects.get('detail') if not success else "")
    
    def test_meetings_management(self):
        """Test meetings CRUD operations"""
        print("\n📅 Testing Meetings Management...")
        
        if not self.token:
            print("❌ No authentication token available for meetings tests")
            return
            
        # Need a project ID for meeting creation
        if not self.created_resources['projects']:
            print("❌ No projects available for meeting tests")
            return
            
        project_id = self.created_resources['projects'][0].get('id')
        
        # Create meeting
        meeting_data = {
            "project_id": project_id,
            "meeting_date": datetime.now(timezone.utc).isoformat(),
            "mode": "online",
            "attendees": ["Client CEO", "Project Manager"],
            "duration_minutes": 60,
            "notes": "Kickoff meeting to discuss project scope",
            "is_delivered": True
        }
        
        success, response = self.make_request('POST', 'meetings', meeting_data, 200)
        self.log_test("Create meeting", success, response.get('detail') if not success else "")
        
        if success:
            self.created_resources['meetings'].append(response)
        
        # Test get all meetings
        success, all_meetings = self.make_request('GET', 'meetings', None, 200)
        self.log_test("Get all meetings", success, all_meetings.get('detail') if not success else "")
        
        # Test get meetings filtered by project
        success, project_meetings = self.make_request('GET', f'meetings?project_id={project_id}', None, 200)
        self.log_test("Filter meetings by project", success, project_meetings.get('detail') if not success else "")
    
    def test_dashboard_stats(self):
        """Test dashboard statistics endpoint"""
        print("\n📈 Testing Dashboard Stats...")
        
        if not self.token:
            print("❌ No authentication token available for dashboard tests")
            return
            
        success, response = self.make_request('GET', 'stats/dashboard', None, 200)
        self.log_test("Get dashboard stats", success, response.get('detail') if not success else "")
        
        if success:
            expected_keys = ['total_leads', 'new_leads', 'qualified_leads', 'closed_deals', 'active_projects']
            for key in expected_keys:
                if key in response:
                    self.log_test(f"Dashboard stats contains {key}", True)
                else:
                    self.log_test(f"Dashboard stats contains {key}", False, f"Missing key: {key}")
    
    def test_role_permissions(self):
        """Test role-based access control"""
        print("\n🔒 Testing Role-based Permissions...")
        
        # Test with manager role (should have limited access)
        manager_users = [u for u in self.created_resources['users'] if u.get('role') == 'manager']
        if manager_users:
            manager_email = manager_users[0].get('email')
            
            # Login as manager
            login_data = {"email": manager_email, "password": "TestPass123!"}
            success, login_response = self.make_request('POST', 'auth/login', login_data, 200)
            
            if success:
                manager_token = login_response.get('access_token')
                old_token = self.token
                self.token = manager_token
                
                # Try to create a lead (should fail for manager)
                lead_data = {"first_name": "Manager", "last_name": "Test", "company": "Test Corp"}
                success, response = self.make_request('POST', 'leads', lead_data, 403)
                self.log_test("Manager cannot create lead", success, "Manager should not be able to create leads")
                
                # Try to create a project (should fail for manager)
                project_data = {
                    "name": "Manager Project",
                    "client_name": "Test Client",
                    "start_date": datetime.now(timezone.utc).isoformat()
                }
                success, response = self.make_request('POST', 'projects', project_data, 403)
                self.log_test("Manager cannot create project", success, "Manager should not be able to create projects")
                
                # Restore admin token
                self.token = old_token
    
    def run_all_tests(self):
        """Run all test suites"""
        print("🚀 Starting Consulting Workflow Management API Tests...")
        print(f"📡 Testing against: {self.base_url}")
        
        try:
            self.test_user_registration_and_login()
            self.test_leads_management()
            self.test_projects_management()
            self.test_meetings_management()
            self.test_dashboard_stats()
            self.test_role_permissions()
        except Exception as e:
            print(f"❌ Test suite failed with error: {e}")
        
        # Print summary
        print(f"\n📊 Test Summary:")
        print(f"   Tests Run: {self.tests_run}")
        print(f"   Tests Passed: {self.tests_passed}")
        print(f"   Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"   Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%" if self.tests_run > 0 else "   Success Rate: 0%")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return 0
        else:
            print("⚠️  Some tests failed!")
            return 1

def main():
    tester = ConsultingWorkflowTester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())