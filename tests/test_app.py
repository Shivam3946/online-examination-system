import os, tempfile, unittest
import app as exam_app

class ExamSystemTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.NamedTemporaryFile(delete=False); self.tmp.close()
        exam_app.DB_PATH=self.tmp.name
        exam_app.init_db()
        exam_app.app.config.update(TESTING=True,SECRET_KEY="test-secret")
        self.client=exam_app.app.test_client()
    def tearDown(self):
        os.unlink(self.tmp.name)
    def login(self,user,pw):
        page=self.client.get("/login")
        # extract token from rendered page
        import re
        token=re.search(r'name="_csrf" value="([^"]+)"',page.get_data(as_text=True)).group(1)
        return self.client.post("/login",data={"username":user,"password":pw,"_csrf":token},follow_redirects=True)
    def test_student_login_and_dashboard(self):
        r=self.login("student","student123")
        self.assertEqual(r.status_code,200)
        self.assertIn(b"Available examinations",r.data)
    def test_wrong_password(self):
        r=self.login("student","wrong")
        self.assertIn(b"Invalid username or password",r.data)
    def test_student_cannot_open_admin_dashboard(self):
        self.login("student","student123")
        r=self.client.get("/admin/user/new")
        self.assertIn(r.status_code,[403,405])
    def test_seed_exam_exists(self):
        with exam_app.db() as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM questions").fetchone()[0],5)

if __name__=="__main__": unittest.main()
