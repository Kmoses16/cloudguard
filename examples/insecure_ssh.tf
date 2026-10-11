# Intentionally insecure example for static scanning only.
# Do not deploy.

resource "aws_security_group" "insecure_ssh" {
  name        = "cloudguard-insecure-ssh-example"
  description = "Training example allowing SSH from any IPv4 address"

  ingress {
    description = "SSH from anywhere"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}