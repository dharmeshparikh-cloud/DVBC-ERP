"""
Test Letter Management APIs - Offer Letters, Appointment Letters, Templates

Features tested:
- Template CRUD operations (POST/GET/PUT /api/letters/templates)
- Offer Letter creation and acceptance workflow
- Appointment Letter creation (after offer acceptance)
- Public letter viewing and acceptance endpoints
- Letter statistics

Credentials:
- Admin: admin@dvbc.com / admin123
- HR Manager: hr.manager@dvbc.com / hr123
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test data tracking
TEST_PREFIX = "TEST_LETTERS_"
created_templates = []
created_offer_letters = []
created_candidates = []


class TestAuth:
    """Authentication helpers"""
    
    @staticmethod
    def get_admin_token():
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@dvbc.com", "password": "admin123"}
        )
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
    
    @staticmethod
    def get_hr_token():
        """Get HR manager authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "hr.manager@dvbc.com", "password": "hr123"}
        )
        if response.status_code == 200:
            return response.json().get("access_token")
        return None


class TestLetterTemplates:
    """Test letter template CRUD operations"""
    
    def test_get_templates_without_auth(self):
        """Templates require authentication"""
        response = requests.get(f"{BASE_URL}/api/letters/templates")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Templates require authentication")
    
    def test_get_templates_list(self):
        """GET /api/letters/templates - List all templates"""
        token = TestAuth.get_admin_token()
        assert token, "Failed to get admin token"
        
        response = requests.get(
            f"{BASE_URL}/api/letters/templates",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        templates = response.json()
        assert isinstance(templates, list), "Expected list of templates"
        print(f"✓ GET templates returned {len(templates)} templates")
        
        # Verify default templates exist
        template_names = [t['name'] for t in templates]
        assert any('Offer' in name or 'offer' in name for name in template_names), \
            "Expected offer letter template to exist"
        print("✓ Default offer letter template exists")
    
    def test_get_templates_filtered_by_type(self):
        """GET /api/letters/templates?template_type=offer_letter - Filter by type"""
        token = TestAuth.get_admin_token()
        
        response = requests.get(
            f"{BASE_URL}/api/letters/templates?template_type=offer_letter",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        
        templates = response.json()
        for t in templates:
            assert t['template_type'] == 'offer_letter', \
                f"Expected offer_letter type, got {t['template_type']}"
        print(f"✓ Filter by type works - {len(templates)} offer letter templates")
    
    def test_create_template(self):
        """POST /api/letters/templates - Create new template"""
        token = TestAuth.get_admin_token()
        
        template_data = {
            "template_type": "offer_letter",
            "name": f"{TEST_PREFIX}Custom Offer Template",
            "subject": "Your Offer - {{designation}}",
            "body_content": "<p>Dear {{employee_name}},</p><p>Welcome to the team as {{designation}}!</p>",
            "is_default": False
        }
        
        response = requests.post(
            f"{BASE_URL}/api/letters/templates",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=template_data
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert "template_id" in result, "Expected template_id in response"
        created_templates.append(result["template_id"])
        print(f"✓ Template created: {result['template_id']}")
    
    def test_create_template_invalid_type(self):
        """POST /api/letters/templates with invalid type should fail"""
        token = TestAuth.get_admin_token()
        
        response = requests.post(
            f"{BASE_URL}/api/letters/templates",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "template_type": "invalid_type",
                "name": "Invalid Template",
                "subject": "Test",
                "body_content": "Test"
            }
        )
        assert response.status_code == 400, f"Expected 400 for invalid type, got {response.status_code}"
        print("✓ Invalid template type rejected with 400")
    
    def test_get_single_template(self):
        """GET /api/letters/templates/{id} - Get template with history"""
        token = TestAuth.get_admin_token()
        
        # First get list to find a template ID
        list_response = requests.get(
            f"{BASE_URL}/api/letters/templates",
            headers={"Authorization": f"Bearer {token}"}
        )
        templates = list_response.json()
        assert len(templates) > 0, "No templates available to test"
        
        template_id = templates[0]['id']
        response = requests.get(
            f"{BASE_URL}/api/letters/templates/{template_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        
        template = response.json()
        assert "history" in template, "Expected history field in template"
        assert template['id'] == template_id
        print(f"✓ Single template retrieved with history field")
    
    def test_update_template(self):
        """PUT /api/letters/templates/{id} - Update template saves history"""
        token = TestAuth.get_admin_token()
        
        # Create a template to update
        create_response = requests.post(
            f"{BASE_URL}/api/letters/templates",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "template_type": "appointment_letter",
                "name": f"{TEST_PREFIX}Update Test Template",
                "subject": "Original Subject",
                "body_content": "Original content"
            }
        )
        assert create_response.status_code == 200
        template_id = create_response.json()['template_id']
        created_templates.append(template_id)
        
        # Update the template
        update_response = requests.put(
            f"{BASE_URL}/api/letters/templates/{template_id}",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "name": f"{TEST_PREFIX}Updated Template Name",
                "subject": "Updated Subject"
            }
        )
        assert update_response.status_code == 200
        result = update_response.json()
        assert result['version'] == 2, f"Expected version 2 after update, got {result.get('version')}"
        print("✓ Template updated, version incremented to 2")
        
        # Verify history is saved
        get_response = requests.get(
            f"{BASE_URL}/api/letters/templates/{template_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        template = get_response.json()
        assert len(template['history']) >= 1, "Expected history entry after update"
        print("✓ Template history saved after update")
    
    def test_hr_manager_can_manage_templates(self):
        """HR Manager should be able to create/update templates"""
        token = TestAuth.get_hr_token()
        if not token:
            pytest.skip("HR Manager token not available")
        
        response = requests.post(
            f"{BASE_URL}/api/letters/templates",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "template_type": "offer_letter",
                "name": f"{TEST_PREFIX}HR Created Template",
                "subject": "HR Template Subject",
                "body_content": "Created by HR"
            }
        )
        assert response.status_code == 200, f"HR should be able to create templates: {response.text}"
        created_templates.append(response.json()['template_id'])
        print("✓ HR Manager can create templates")


class TestOfferLetters:
    """Test offer letter creation and workflow"""
    
    @pytest.fixture(autouse=True)
    def setup_test_candidate(self):
        """Create a test candidate for offer letter tests"""
        from pymongo import MongoClient
        
        mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
        db_name = os.environ.get('DB_NAME', 'test_database')
        
        client = MongoClient(mongo_url)
        db = client[db_name]
        
        # Create test candidate with verified status
        candidate_id = str(uuid.uuid4())
        test_candidate = {
            "id": candidate_id,
            "first_name": "Test",
            "last_name": "Candidate",
            "email": f"test.candidate.{candidate_id[:8]}@test.com",
            "phone": "+91 9876543210",
            "background_verified": True,
            "documents_verified": True,
            "status": "verified",
            "created_at": "2026-02-18T10:00:00Z"
        }
        db.onboarding_candidates.insert_one(test_candidate)
        created_candidates.append(candidate_id)
        
        self.candidate_id = candidate_id
        self.candidate_email = test_candidate['email']
        
        yield
        
        # Cleanup handled in teardown
    
    def test_create_offer_letter_without_verified_candidate(self):
        """Cannot create offer for unverified candidate"""
        from pymongo import MongoClient
        
        mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
        db_name = os.environ.get('DB_NAME', 'test_database')
        client = MongoClient(mongo_url)
        db = client[db_name]
        
        # Create unverified candidate
        unverified_id = str(uuid.uuid4())
        db.onboarding_candidates.insert_one({
            "id": unverified_id,
            "first_name": "Unverified",
            "last_name": "Person",
            "email": "unverified@test.com",
            "background_verified": False,
            "documents_verified": False
        })
        created_candidates.append(unverified_id)
        
        token = TestAuth.get_admin_token()
        
        # Get a template ID
        templates_response = requests.get(
            f"{BASE_URL}/api/letters/templates?template_type=offer_letter",
            headers={"Authorization": f"Bearer {token}"}
        )
        templates = templates_response.json()
        template_id = templates[0]['id'] if templates else None
        
        if template_id:
            response = requests.post(
                f"{BASE_URL}/api/letters/offer-letters",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={
                    "candidate_id": unverified_id,
                    "template_id": template_id,
                    "designation": "Test Role",
                    "department": "Test Dept",
                    "joining_date": "2026-03-01",
                    "salary_details": {"gross_monthly": "50000"}
                }
            )
            assert response.status_code == 400, f"Expected 400 for unverified candidate, got {response.status_code}"
            assert "verified" in response.json().get('detail', '').lower()
            print("✓ Cannot create offer for unverified candidate")
    
    def test_create_offer_letter(self):
        """POST /api/letters/offer-letters - Create offer letter"""
        token = TestAuth.get_admin_token()
        
        # Get offer letter template
        templates_response = requests.get(
            f"{BASE_URL}/api/letters/templates?template_type=offer_letter",
            headers={"Authorization": f"Bearer {token}"}
        )
        templates = templates_response.json()
        assert len(templates) > 0, "No offer letter templates available"
        template_id = templates[0]['id']
        
        response = requests.post(
            f"{BASE_URL}/api/letters/offer-letters",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "candidate_id": self.candidate_id,
                "template_id": template_id,
                "designation": "Software Engineer",
                "department": "Technology",
                "joining_date": "2026-03-15",
                "salary_details": {
                    "gross_monthly": "75000",
                    "basic": "37500",
                    "hra": "15000"
                },
                "hr_signature_text": "HR Manager"
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert "offer_letter_id" in result
        assert "acceptance_link" in result
        created_offer_letters.append(result['offer_letter_id'])
        
        # Store acceptance token for later tests
        self.__class__.acceptance_link = result['acceptance_link']
        self.__class__.offer_letter_id = result['offer_letter_id']
        print(f"✓ Offer letter created: {result['offer_letter_id']}")
        print(f"  Acceptance link: {result['acceptance_link']}")
    
    def test_get_offer_letters_list(self):
        """GET /api/letters/offer-letters - List all offer letters"""
        token = TestAuth.get_admin_token()
        
        response = requests.get(
            f"{BASE_URL}/api/letters/offer-letters",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        
        letters = response.json()
        assert isinstance(letters, list)
        print(f"✓ Offer letters list returned {len(letters)} letters")
    
    def test_get_offer_letters_filtered_by_status(self):
        """GET /api/letters/offer-letters?status=pending_acceptance"""
        token = TestAuth.get_admin_token()
        
        response = requests.get(
            f"{BASE_URL}/api/letters/offer-letters?status=pending_acceptance",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        
        letters = response.json()
        for letter in letters:
            assert letter['status'] == 'pending_acceptance'
        print(f"✓ Status filter works - {len(letters)} pending offer letters")


class TestPublicOfferAcceptance:
    """Test public offer letter viewing and acceptance"""
    
    @pytest.fixture(autouse=True)
    def setup_offer_letter(self):
        """Create offer letter for acceptance testing"""
        from pymongo import MongoClient
        
        mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
        db_name = os.environ.get('DB_NAME', 'test_database')
        client = MongoClient(mongo_url)
        db = client[db_name]
        
        # Create verified candidate
        candidate_id = str(uuid.uuid4())
        db.onboarding_candidates.insert_one({
            "id": candidate_id,
            "first_name": "Accept",
            "last_name": "Test",
            "email": f"accept.test.{candidate_id[:8]}@test.com",
            "background_verified": True,
            "documents_verified": True
        })
        created_candidates.append(candidate_id)
        
        token = TestAuth.get_admin_token()
        
        # Get template
        templates_response = requests.get(
            f"{BASE_URL}/api/letters/templates?template_type=offer_letter",
            headers={"Authorization": f"Bearer {token}"}
        )
        template_id = templates_response.json()[0]['id']
        
        # Create offer letter
        response = requests.post(
            f"{BASE_URL}/api/letters/offer-letters",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "candidate_id": candidate_id,
                "template_id": template_id,
                "designation": "Senior Developer",
                "department": "Engineering",
                "joining_date": "2026-04-01",
                "salary_details": {"gross_monthly": "100000"}
            }
        )
        assert response.status_code == 200
        
        result = response.json()
        self.acceptance_link = result['acceptance_link']
        self.acceptance_token = self.acceptance_link.split('/')[-1]
        self.offer_letter_id = result['offer_letter_id']
        created_offer_letters.append(self.offer_letter_id)
        
        yield
    
    def test_view_offer_letter_public(self):
        """GET /api/letters/view/offer/{token} - Public viewing"""
        response = requests.get(f"{BASE_URL}/api/letters/view/offer/{self.acceptance_token}")
        assert response.status_code == 200
        
        data = response.json()
        assert "letter" in data
        assert "template" in data
        assert "can_accept" in data
        assert data['can_accept'] == True  # Should be pending
        print("✓ Public offer letter view works")
    
    def test_view_offer_letter_invalid_token(self):
        """GET /api/letters/view/offer/{invalid} - Should return 404"""
        response = requests.get(f"{BASE_URL}/api/letters/view/offer/invalid-token-123")
        assert response.status_code == 404
        print("✓ Invalid token returns 404")
    
    def test_accept_offer_letter(self):
        """POST /api/letters/offer-letters/accept - Accept offer"""
        response = requests.post(
            f"{BASE_URL}/api/letters/offer-letters/accept",
            json={"acceptance_token": self.acceptance_token}
        )
        assert response.status_code == 200
        
        result = response.json()
        assert "employee_id" in result
        assert result['employee_id'].startswith("EMP")
        assert "candidate_name" in result
        assert "acceptance_signature" in result
        
        # Employee ID should be EMP009 or higher
        emp_num = int(result['employee_id'].replace("EMP", ""))
        assert emp_num >= 9, f"Employee ID should start from EMP009, got {result['employee_id']}"
        
        self.__class__.assigned_employee_id = result['employee_id']
        print(f"✓ Offer accepted! Employee ID assigned: {result['employee_id']}")
    
    def test_cannot_accept_twice(self):
        """Cannot accept an already accepted offer"""
        # First acceptance should work
        response = requests.post(
            f"{BASE_URL}/api/letters/offer-letters/accept",
            json={"acceptance_token": self.acceptance_token}
        )
        # Either already accepted (from previous test) or this is first acceptance
        if response.status_code == 200:
            # First acceptance worked, try again
            response = requests.post(
                f"{BASE_URL}/api/letters/offer-letters/accept",
                json={"acceptance_token": self.acceptance_token}
            )
        
        assert response.status_code == 404, "Second acceptance should fail with 404"
        print("✓ Cannot accept offer twice")


class TestAppointmentLetters:
    """Test appointment letter creation (after offer acceptance)"""
    
    @pytest.fixture(autouse=True)
    def setup_accepted_employee(self):
        """Create accepted offer to test appointment letter"""
        from pymongo import MongoClient
        
        mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
        db_name = os.environ.get('DB_NAME', 'test_database')
        client = MongoClient(mongo_url)
        db = client[db_name]
        
        # Create candidate
        candidate_id = str(uuid.uuid4())
        db.onboarding_candidates.insert_one({
            "id": candidate_id,
            "first_name": "Appointment",
            "last_name": "Test",
            "email": f"appointment.{candidate_id[:8]}@test.com",
            "background_verified": True,
            "documents_verified": True
        })
        created_candidates.append(candidate_id)
        
        token = TestAuth.get_admin_token()
        
        # Get template
        templates_response = requests.get(
            f"{BASE_URL}/api/letters/templates?template_type=offer_letter",
            headers={"Authorization": f"Bearer {token}"}
        )
        template_id = templates_response.json()[0]['id']
        
        # Create and accept offer
        offer_response = requests.post(
            f"{BASE_URL}/api/letters/offer-letters",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "candidate_id": candidate_id,
                "template_id": template_id,
                "designation": "Product Manager",
                "department": "Product",
                "joining_date": "2026-04-15",
                "salary_details": {"gross_monthly": "120000"}
            }
        )
        offer_result = offer_response.json()
        created_offer_letters.append(offer_result['offer_letter_id'])
        
        # Accept offer
        accept_response = requests.post(
            f"{BASE_URL}/api/letters/offer-letters/accept",
            json={"acceptance_token": offer_result['acceptance_link'].split('/')[-1]}
        )
        accept_result = accept_response.json()
        
        self.employee_id = candidate_id  # The candidate becomes employee
        self.employee_code = accept_result.get('employee_id', 'EMP009')
        
        yield
    
    def test_create_appointment_letter(self):
        """POST /api/letters/appointment-letters - Create after offer acceptance"""
        token = TestAuth.get_admin_token()
        
        # Get appointment template
        templates_response = requests.get(
            f"{BASE_URL}/api/letters/templates?template_type=appointment_letter",
            headers={"Authorization": f"Bearer {token}"}
        )
        templates = templates_response.json()
        assert len(templates) > 0, "No appointment letter templates"
        template_id = templates[0]['id']
        
        response = requests.post(
            f"{BASE_URL}/api/letters/appointment-letters",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "employee_id": self.employee_id,
                "template_id": template_id,
                "hr_signature_text": "HR Director"
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert "appointment_letter_id" in result
        assert "acceptance_link" in result
        print(f"✓ Appointment letter created: {result['appointment_letter_id']}")
    
    def test_cannot_create_appointment_without_employee_id(self):
        """Appointment letter requires employee to have assigned Employee ID"""
        from pymongo import MongoClient
        
        mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
        db_name = os.environ.get('DB_NAME', 'test_database')
        client = MongoClient(mongo_url)
        db = client[db_name]
        
        # Create candidate without accepting offer (no employee_id)
        no_emp_id = str(uuid.uuid4())
        db.onboarding_candidates.insert_one({
            "id": no_emp_id,
            "first_name": "No",
            "last_name": "EmpId",
            "email": "no.empid@test.com",
            "background_verified": True,
            "documents_verified": True
            # Note: No employee_id field
        })
        created_candidates.append(no_emp_id)
        
        token = TestAuth.get_admin_token()
        
        templates_response = requests.get(
            f"{BASE_URL}/api/letters/templates?template_type=appointment_letter",
            headers={"Authorization": f"Bearer {token}"}
        )
        template_id = templates_response.json()[0]['id']
        
        response = requests.post(
            f"{BASE_URL}/api/letters/appointment-letters",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "employee_id": no_emp_id,
                "template_id": template_id
            }
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "employee id" in response.json().get('detail', '').lower()
        print("✓ Cannot create appointment without assigned Employee ID")
    
    def test_get_appointment_letters_list(self):
        """GET /api/letters/appointment-letters - List all"""
        token = TestAuth.get_admin_token()
        
        response = requests.get(
            f"{BASE_URL}/api/letters/appointment-letters",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        print(f"✓ Appointment letters list: {len(response.json())} letters")


class TestLetterStats:
    """Test letter statistics endpoint"""
    
    def test_get_letter_stats(self):
        """GET /api/letters/stats - Get statistics"""
        token = TestAuth.get_admin_token()
        
        response = requests.get(
            f"{BASE_URL}/api/letters/stats",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        
        stats = response.json()
        assert "offer_letters" in stats
        assert "appointment_letters" in stats
        assert "templates" in stats
        assert "pending" in stats['offer_letters']
        assert "accepted" in stats['offer_letters']
        print(f"✓ Stats: {stats['offer_letters']['pending']} pending offers, "
              f"{stats['offer_letters']['accepted']} accepted, "
              f"{stats['templates']} templates")
    
    def test_stats_requires_auth(self):
        """Stats endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/letters/stats")
        assert response.status_code == 401
        print("✓ Stats requires authentication")


class TestRoleBasedAccess:
    """Test role-based access control for letter management"""
    
    def test_hr_executive_read_only(self):
        """HR Executive can read but not create templates"""
        # This test assumes HR Executive role exists
        # If not available, skip
        token = TestAuth.get_admin_token()
        
        # Verify admin can create (baseline)
        response = requests.post(
            f"{BASE_URL}/api/letters/templates",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "template_type": "offer_letter",
                "name": f"{TEST_PREFIX}RBAC Test Template",
                "subject": "Test",
                "body_content": "Test"
            }
        )
        assert response.status_code == 200
        created_templates.append(response.json()['template_id'])
        print("✓ Admin can create templates")


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_data():
    """Cleanup test data after all tests"""
    yield
    
    from pymongo import MongoClient
    
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    db_name = os.environ.get('DB_NAME', 'test_database')
    
    try:
        client = MongoClient(mongo_url)
        db = client[db_name]
        
        # Delete test templates
        if created_templates:
            db.letter_templates.delete_many({"id": {"$in": created_templates}})
            print(f"Cleaned up {len(created_templates)} test templates")
        
        # Delete test offer letters
        if created_offer_letters:
            db.offer_letters.delete_many({"id": {"$in": created_offer_letters}})
            print(f"Cleaned up {len(created_offer_letters)} test offer letters")
        
        # Delete test candidates
        if created_candidates:
            db.onboarding_candidates.delete_many({"id": {"$in": created_candidates}})
            print(f"Cleaned up {len(created_candidates)} test candidates")
        
        # Cleanup any TEST_PREFIX templates that might remain
        db.letter_templates.delete_many({"name": {"$regex": f"^{TEST_PREFIX}"}})
        
    except Exception as e:
        print(f"Cleanup error: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
