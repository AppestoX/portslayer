class Portslayer < Formula
  include Language::Python::Virtualenv

  desc "Cross-platform terminal tool to inspect and kill processes by port"
  homepage "https://github.com/AppestoX/portslayer-cli"
  url "https://files.pythonhosted.org/packages/source/p/portslayer/portslayer-1.1.0.tar.gz"
  sha256 "REPLACE_WITH_SDIST_SHA256_AFTER_PYPI_PUBLISH"
  license "MIT"

  depends_on "python@3.12"

  # Resource blocks below are placeholders. After publishing to PyPI, run:
  #   pip install homebrew-pypi-poet
  #   poet -f portslayer > resources.rb
  # and paste the generated `resource` blocks here (one per dependency:
  # typer, rich, textual, click, shellingham, markdown-it-py, pygments,
  # linkify-it-py, uc-micro-py, mdit-py-plugins, platformdirs, colorama, mdurl).
  # resource "typer" do
  #   url "https://files.pythonhosted.org/.../typer-X.Y.Z.tar.gz"
  #   sha256 "..."
  # end

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "PortSlayer", shell_output("#{bin}/portslayer --version")
  end
end
