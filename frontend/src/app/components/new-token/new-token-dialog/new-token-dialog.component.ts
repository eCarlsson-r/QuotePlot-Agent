import { Component, Inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MaterialDesignModule } from '../../../modules/material-design/material-design.module';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { ProgressSpinnerService } from '../../../services/progress-spinner.service';
import { SeedTokenFactoryService } from '../../../services/seed-token-factory.service';
 
export interface NewToken {
  name: string;
  symbol: string;
  onCreateNewToken: () => void;
}
 
@Component({
  selector: 'app-new-token-dialog',
  standalone: true,
  imports: [
    FormsModule,
    MaterialDesignModule
  ],
  templateUrl: './new-token-dialog.component.html',
  styleUrl: './new-token-dialog.component.css'
})
export class NewTokenDialogComponent {
  constructor(
    public dialogRef: MatDialogRef<NewTokenDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: NewToken,
    private progressSpinnerService: ProgressSpinnerService,
    private seedTokenFactoryService: SeedTokenFactoryService
  ) {}

  get canCreate(): boolean {
    return Boolean(this.data.name.trim() && this.data.symbol.trim());
  }

  get previewInitial(): string {
    return this.data.symbol.trim().charAt(0).toUpperCase() || '+';
  }

  onCreate() {
    if (!this.canCreate) return;
    this.dialogRef.close();
    const promise = this.seedTokenFactoryService.get().create(
      this.data.name.trim(),
      this.data.symbol.trim()
    );
    this.progressSpinnerService.showSpinnerUntilExecuted(
      promise,
      this.data.onCreateNewToken
    );
  }
 
  onCancel() {
    this.dialogRef.close();
  }
}
