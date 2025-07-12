"""Test PHP language support in tree-sitter analyzer."""

import tempfile
from pathlib import Path

import pytest

from coda.base.search import TreeSitterAnalyzer


class TestPHPSupport:
    """Test tree-sitter analysis for PHP files."""

    def setup_method(self):
        """Set up test environment."""
        self.analyzer = TreeSitterAnalyzer()
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_php_language_detection(self):
        """Test that .php files are detected as PHP."""
        test_file = Path(self.temp_dir) / "test.php"
        test_file.write_text("<?php echo 'Hello'; ?>")

        assert self.analyzer.detect_language(test_file) == "php"

    def test_php_basic_parsing(self):
        """Test basic PHP parsing capabilities."""
        php_code = r"""<?php
namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class User extends Model
{
    protected $fillable = ['name', 'email'];

    public function posts()
    {
        return $this->hasMany(Post::class);
    }
}

interface Authenticatable
{
    public function authenticate(string $password): bool;
}

function helper($data)
{
    return json_encode($data);
}
"""
        test_file = Path(self.temp_dir) / "test.php"
        test_file.write_text(php_code)

        analysis = self.analyzer.analyze_file(test_file)

        assert analysis.language == "php"
        assert len(analysis.imports) > 0
        assert len(analysis.definitions) > 0

        # Check for specific definitions
        class_names = [d.name for d in analysis.definitions if d.kind.value == "class"]
        assert "User" in class_names

        interface_names = [d.name for d in analysis.definitions if d.kind.value == "interface"]
        assert "Authenticatable" in interface_names

        function_names = [d.name for d in analysis.definitions if d.kind.value == "function"]
        assert "helper" in function_names

        method_names = [d.name for d in analysis.definitions if d.kind.value == "method"]
        assert "posts" in method_names
        assert "authenticate" in method_names

    def test_php_namespace_and_imports(self):
        """Test parsing of PHP namespaces and use statements."""
        php_code = r"""<?php
namespace App\Http\Controllers;

use App\Models\User;
use App\Services\UserService;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;

class UserController
{
    // Implementation
}
"""
        test_file = Path(self.temp_dir) / "test.php"
        test_file.write_text(php_code)

        analysis = self.analyzer.analyze_file(test_file)

        # Check namespace
        module_names = [d.name for d in analysis.definitions if d.kind.value == "module"]
        assert r"App\Http\Controllers" in module_names

        # Check imports
        import_names = [imp.name for imp in analysis.imports]
        assert r"App\Models\User" in import_names
        assert r"App\Services\UserService" in import_names
        assert r"Illuminate\Http\Request" in import_names
        assert r"Illuminate\Support\Facades\DB" in import_names


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
