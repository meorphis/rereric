their remote changes
also span
multiple lines
>>>>>>> remote/main
Some context after
More context after
"""
        file_path = self.create_conflict_file(content)
        conflicts = self.fuzzy_rerere._extract_conflict_markers(file_path)
        
        self.assertEqual(len(conflicts), 1)
        self.assertIn("<<<<<<< HEAD", conflicts[0])
        self.assertIn("my local changes", conflicts[0])
        self.assertIn("=======", conflicts[0])
        self.assertIn("their remote changes", conflicts[0])
        self.assertIn(">>>>>>> remote/main", conflicts[0])
        self.assertIn("Some context before", conflicts[0])
        self.assertIn("Some context after", conflicts[0])

    def test_record_resolution(self):
        content = """<<<<<<< HEAD
print("hello")

