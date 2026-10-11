# Static scanning example only.
# The private source range is illustrative, not your actual network.

resource "aws_security_group" "restricted_ssh" {
  name        = "cloudguard-restricted-ssh-example"
  description = "Training example restricting SSH to a private subnet"

  ingress {
    description = "SSH from the example management subnet"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}